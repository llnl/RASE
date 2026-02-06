###############################################################################
# Copyright (c) 2018-2026 Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory
#
# Written by J. Brodsky, J. Chavez, S. Czyz, G. Kosinovsky, V. Mozin,
#            S. Sangiorgio.
#
# RASE-support@llnl.gov.
#
# LLNL-CODE-2014600, LLNL-CODE-829509
#
# All rights reserved.
#
# This file is part of RASE.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED,INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
###############################################################################
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple, Union

from tqdm import tqdm

from openai import OpenAI, AzureOpenAI

try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # type: ignore


GlossaryType = Mapping[str, str]
DoNotTranslateType = Sequence[str]


def _is_path_like(value: Any) -> bool:
    return isinstance(value, (str, os.PathLike)) and len(str(value)) > 0


def _load_json_or_yaml(path: Union[str, os.PathLike]) -> Any:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    text = p.read_text(encoding="utf-8")
    # Prefer JSON first for speed/robustness; fall back to YAML if available
    try:
        return json.loads(text)
    except Exception:
        if yaml is None:
            raise RuntimeError(
                "PyYAML is not installed. Install pyyaml or provide JSON/dict input for glossary/do-not-translate."
            )
        return yaml.safe_load(text)


def _normalize_glossary(obj: Any) -> GlossaryType:
    # Accepts dict[str,str] or list[{source,definition}] or list[tuple]
    if obj is None:
        return {}
    if isinstance(obj, Mapping):
        # Ensure all keys/values are strings
        return {str(k): str(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        result: Dict[str, str] = {}
        for item in obj:
            if isinstance(item, Mapping) and "source" in item and "definition" in item:
                result[str(item["source"]) ] = str(item["definition"])  # type: ignore[index]
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                src, tgt = item
                result[str(src)] = str(tgt)
            else:
                raise ValueError("Unsupported glossary list item; expected {source,definition} or [source,definition].")
        return result
    raise ValueError("Unsupported glossary format; expected dict or list of pairs.")


def _normalize_dnt(obj: Any) -> DoNotTranslateType:
    # Accepts list[str] or dict with key terms or do_not_translate
    if obj is None:
        return []
    if isinstance(obj, (list, tuple)):
        return [str(x) for x in obj]
    if isinstance(obj, Mapping):
        for key in ("do_not_translate", "terms", "words"):
            if key in obj:
                val = obj[key]
                if isinstance(val, (list, tuple)):
                    return [str(x) for x in val]
        # If it's a mapping but none of the expected keys exist, treat values as terms
        return [str(v) for v in obj.values()]
    # If a single string is provided, treat as one protected term
    if isinstance(obj, str):
        return [obj]
    raise ValueError("Unsupported do-not-translate format; expected list or mapping with 'do_not_translate'/'terms'.")


def _collect_ts_examples(ts_paths: Sequence[Union[str, os.PathLike]], limit: int) -> List[Dict[str, str]]:
    pairs: List[Dict[str, str]] = []
    for p in ts_paths:
        try:
            tree = ET.parse(str(p))
        except Exception:
            continue
        root = tree.getroot()
        for context in root.findall("context"):
            for message in context.findall("message"):
                source = message.find("source")
                translation = message.find("translation")
                if source is None or translation is None:
                    continue
                if source.text is None:
                    continue
                # Consider as example only if translation exists and is not unfinished
                if "type" in translation.attrib and translation.attrib.get("type") == "unfinished":
                    continue
                if translation.text is None:
                    continue
                # Only include short strings (< 50 chars) for consistency examples
                if len(source.text) < 50 and len(translation.text) < 50:
                    pairs.append({"source": source.text, "translation": translation.text})
                if len(pairs) >= limit:
                    return pairs
    return pairs[:limit]


@dataclass
class LLMTranslatorConfig:
    model: str = "gpt-5-mini"
    temperature: float = 0.1
    top_p: float = 0.1
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    glossary: Optional[Union[GlossaryType, str, os.PathLike]] = None
    do_not_translate: Optional[Union[DoNotTranslateType, str, os.PathLike]] = None
    max_ts_examples: int = 200


class LLMTranslator:
    """OpenAI-based translator that injects glossary and DNT into every prompt."""

    def __init__(self, config: Optional[LLMTranslatorConfig] = None) -> None:
        cfg = config or LLMTranslatorConfig()

        api_key = cfg.api_key or os.environ.get("OPENAI_API_KEY")
        base_url = cfg.base_url or os.environ.get("OPENAI_API_URL")

        if OpenAI is None:
            raise RuntimeError(
                f"openai package not available: {_openai_import_error!r}"  # type: ignore[name-defined]
            )

        # Use AzureOpenAI for gpt-5 family models; otherwise default OpenAI client
        if str(cfg.model).strip().lower().startswith("gpt-5"):
            api_version = "2025-04-01-preview"
            self._client = AzureOpenAI(  # type: ignore[arg-type]
                api_key=api_key,
                api_version=api_version,
                base_url=base_url,
            )
        else:
            self._client = OpenAI(api_key=api_key, base_url=base_url)  # type: ignore[arg-type]
        self._model = cfg.model
        self._temperature = float(cfg.temperature)
        self._top_p = float(cfg.top_p)
        self._max_ts_examples = int(cfg.max_ts_examples)

        # Normalize glossary and DNT
        glossary = cfg.glossary
        if _is_path_like(glossary):
            glossary = _load_json_or_yaml(glossary)  # type: ignore[arg-type]
        self._glossary: GlossaryType = _normalize_glossary(glossary) if glossary is not None else {}

        dnt = cfg.do_not_translate
        if _is_path_like(dnt):
            dnt = _load_json_or_yaml(dnt)  # type: ignore[arg-type]
        self._do_not_translate: List[str] = list(_normalize_dnt(dnt) if dnt is not None else [])

        # Usage accounting
        self._usage_prompt_tokens: int = 0
        self._usage_completion_tokens: int = 0
        self._usage_total_tokens: int = 0
        self._usage_cache_write_tokens: int = 0
        self._usage_cache_read_tokens: int = 0
        # Feature toggle: disable cache_control if upstream rejects it
        self._cache_control_supported: bool = True
        # Deterministic caches for examples per path-set
        self._examples_cache: Dict[Tuple[str, ...], List[Dict[str, str]]] = {}

    @property
    def model(self) -> str:
        return self._model

    def translate(
        self,
        text: str,
        output_lang: str,
        ts_example_paths: Optional[Sequence[Union[str, os.PathLike]]] = None,
    ) -> str:
        """Translate one message.

        Args:
            text: Source text in English.
            output_lang: Target language name (e.g., "Italian", "German").
            ts_example_paths: Optional .ts files to mine example pairs from.

        Returns:
            The translated text as produced by the model.
        """
        # Deterministic examples and glossary/DNT
        examples: List[Dict[str, str]] = []
        if ts_example_paths:
            key = tuple(str(Path(p)) for p in ts_example_paths)
            if key not in self._examples_cache:
                self._examples_cache[key] = _collect_ts_examples(ts_example_paths, limit=self._max_ts_examples)
            examples = self._examples_cache[key]

        sorted_glossary_items = sorted(self._glossary.items(), key=lambda kv: (kv[0].lower(), kv[1].lower()))
        sorted_dnt = sorted(self._do_not_translate, key=lambda s: s.lower())

        control_payload = {
            "type": "translation_control",
            "target_language": output_lang,
            "constraints": {
                "preserve_placeholders_and_formatting": True,
                "preserve_line_breaks_and_leading_or_trailing_spaces": True,
                "return_only_translation_text": True,
                "no_explanations_or_quotes": True,
            },
            "glossary": [{"source": k, "definition": v} for k, v in sorted_glossary_items],
            "rules": {
                "do_not_translate": sorted_dnt,
                "existing_translation_examples": examples,
            },
        }

        system_instructions = (
            "You are a strict AI translator for a software GUI named RASE. \n"
            "RASE is a QT-based software for generating and analyzing synthetic gamma-ray spectra of radiation detectors. \n\n"
            "Translate from English to the target language. \n"
            "Honor the machine-readable control JSON and use the glossary to inform translation choices. \n"
            "IMPORTANT: You MUST preserve punctuation, capitalization (e.g. title case or sentence case), HTML, special characters, line breaks, and placeholders like %s, {name}, etc. \n"
            "Preserve all leading and trailing spaces and all line breaks. \n"
            "Output must be ONLY the translated text. \n"
        )

        cached_control_json = json.dumps(control_payload, ensure_ascii=False, separators=(",", ":"))

        def build_input(use_cache: bool) -> List[Dict[str, Any]]:
            sys_parts: List[Dict[str, Any]] = []
            if use_cache:
                sys_parts.append({"type": "input_text", "text": system_instructions, "cache_control": {"type": "ephemeral"}})
                sys_parts.append({"type": "input_text", "text": cached_control_json, "cache_control": {"type": "ephemeral"}})
            else:
                sys_parts.append({"type": "input_text", "text": system_instructions})
                sys_parts.append({"type": "input_text", "text": cached_control_json})
            return [
                {"role": "system", "content": sys_parts},
                {"role": "user", "content": [{"type": "input_text", "text": text}]},
            ]
        
        # print(json.dumps(build_input(self._cache_control_supported), indent=4))

        try:
            # Add reasoning + verbosity for gpt-5 family
            request_kwargs: Dict[str, Any] = {
                "model": self._model,
                "input": build_input(self._cache_control_supported),
            }
            if str(self._model).strip().lower().startswith("gpt-5"):
                request_kwargs["reasoning"] = {"effort": "low"}
                request_kwargs["text"] = {"verbosity": "low"}
            else:
                request_kwargs["temperature"] = self._temperature
                request_kwargs["top_p"] = self._top_p

            resp = self._client.responses.create(**request_kwargs)
        except Exception as e:
            msg = str(e)
            if "cache_control" in msg and "Unknown parameter" in msg:
                # Retry without cache_control for providers that don't support it
                self._cache_control_supported = False
                request_kwargs_retry: Dict[str, Any] = {
                    "model": self._model,
                    "input": build_input(False),
                }
                if str(self._model).strip().lower().startswith("gpt-5"):
                    request_kwargs_retry["reasoning"] = {"effort": "low"}
                    request_kwargs_retry["text"] = {"verbosity": "low"}
                else:
                    request_kwargs_retry["temperature"] = self._temperature
                    request_kwargs_retry["top_p"] = self._top_p

                resp = self._client.responses.create(**request_kwargs_retry)
            else:
                raise

        # Track token usage if available (Responses API fields)
        usage = getattr(resp, "usage", None)
        if usage is not None:
            prompt_tokens = getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", None)
            completion_tokens = getattr(usage, "completion_tokens", None) or getattr(usage, "output_tokens", None)
            total_tokens = getattr(usage, "total_tokens", None)

            # Prefer OpenAI's prompt caching field when available
            cached_prompt_tokens = None
            ptd = getattr(usage, "prompt_tokens_details", None)
            if ptd is not None:
                cached_prompt_tokens = getattr(ptd, "cached_tokens", None)
                if cached_prompt_tokens is None and isinstance(ptd, dict):
                    cached_prompt_tokens = ptd.get("cached_tokens")

            # Fallback to provider-specific fields for cache read/write
            cache_write = getattr(usage, "cache_creation_input_tokens", None)
            cache_read = getattr(usage, "cache_read_input_tokens", None)

            if isinstance(usage, dict):
                prompt_tokens = prompt_tokens or usage.get("input_tokens", 0)
                completion_tokens = completion_tokens or usage.get("output_tokens", 0)
                total_tokens = total_tokens or usage.get("total_tokens", 0)
                # dict fallbacks for cache metrics
                cache_write = cache_write or usage.get("cache_creation_input_tokens", 0)
                cache_read = cache_read or usage.get("cache_read_input_tokens", 0)
                if cached_prompt_tokens is None:
                    ptd_dict = usage.get("prompt_tokens_details")
                    if isinstance(ptd_dict, dict):
                        cached_prompt_tokens = ptd_dict.get("cached_tokens")

            # If OpenAI-style cached tokens are present, treat them as cache reads
            if cached_prompt_tokens is not None:
                cache_read = cached_prompt_tokens

            if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
                try:
                    total_tokens = int(prompt_tokens) + int(completion_tokens)
                except Exception:
                    total_tokens = 0

            try:
                self._usage_prompt_tokens += int(prompt_tokens or 0)
                self._usage_completion_tokens += int(completion_tokens or 0)
                self._usage_total_tokens += int(total_tokens or 0)
                self._usage_cache_write_tokens += int(cache_write or 0)
                self._usage_cache_read_tokens += int(cache_read or 0)
            except Exception:
                pass

        # Extract output text from Responses API
        output_text = getattr(resp, "output_text", None)
        if isinstance(output_text, str) and output_text:
            return output_text
        out = getattr(resp, "output", None)
        if isinstance(out, list) and out:
            first = out[0]
            content = getattr(first, "content", None)
            if isinstance(content, list) and content:
                text_part = getattr(content[0], "text", None)
                if isinstance(text_part, str) and text_part:
                    return text_part
        raise RuntimeError("Model returned empty content.")

    def usage_summary(self) -> Dict[str, int]:
        return {
            "prompt_tokens": self._usage_prompt_tokens,
            "completion_tokens": self._usage_completion_tokens,
            "total_tokens": self._usage_total_tokens,
            "cache_write_tokens": self._usage_cache_write_tokens,
            "cache_read_tokens": self._usage_cache_read_tokens,
        }

    def process_ts_file(
        self,
        input_file: Union[str, os.PathLike],
        output_file: Union[str, os.PathLike],
        output_lang: str,
        max_entries: Optional[int] = None,
    ) -> Tuple[int, int]:
        """Translate all unfinished messages in a Qt .ts file.

        Returns a tuple (translated_count, total_candidates).
        """
        try:
            tree = ET.parse(str(input_file))
        except ET.ParseError as e:
            print(f"Error parsing XML: {e}")
            return (0, 0)

        root = tree.getroot()

        messages_to_translate: List[ET.Element] = []
        for context in root.findall("context"):
            for message in context.findall("message"):
                source = message.find("source")
                translation = message.find("translation")
                if source is None or translation is None or not (source.text):
                    continue
                if "type" in translation.attrib and translation.attrib.get("type") == "unfinished":
                    messages_to_translate.append(message)

        if max_entries is not None:
            messages_to_translate = messages_to_translate[: max(0, int(max_entries))]

        translated = 0
        for message in tqdm(messages_to_translate, desc="Translating messages", unit="msg"):
            source = message.find("source")
            translation = message.find("translation")
            assert source is not None and translation is not None
            result = self.translate(
                text=source.text or "",
                output_lang=output_lang,
                ts_example_paths=[input_file],
            )
            
            # print(f"source: {source.text}")
            # print(f"transl: {result}")

            translation.text = result
            if "type" in translation.attrib:
                del translation.attrib["type"]
            translated += 1

        tree.write(str(output_file), encoding="utf-8", xml_declaration=True)
        return (translated, len(messages_to_translate))


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Translate a Qt .ts file using OpenAI API.")
    p.add_argument("output_lang", type=str, help="Output language for translation (e.g., Italian)")
    p.add_argument("input_file", type=str, help="Input .ts file to translate (in-place by default)")
    p.add_argument("--max_entries", "-m", type=int, default=None, help="Max number of strings to process")

    # Model/config overrides
    p.add_argument("--model", type=str, default="gpt-5-mini", help="OpenAI model name")
    p.add_argument("--temperature", type=float, default=0.1, help="Sampling temperature")
    p.add_argument("--top_p", type=float, default=0.1, help="Top-p nucleus sampling")
    p.add_argument("--api_key", type=str, default=None, help="OpenAI API key (defaults to OPENAI_API_KEY)")
    p.add_argument("--base_url", type=str, default=None, help="OpenAI API base URL (defaults to OPENAI_API_URL)")

    # Glossary and DNT
    p.add_argument(
        "--glossary",
        type=str,
        default=None,
        help="Path to glossary (YAML/JSON) mapping source->definition, or omit to use none",
    )
    p.add_argument(
        "--do_not_translate",
        type=str,
        default=None,
        help="Path to list (YAML/JSON) of protected terms that must not be translated",
    )
    p.add_argument(
        "--max_ts_examples",
        type=int,
        default=200,
        help="Max number of existing translations from .ts to include as examples (used for prompt caching).",
    )
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_arg_parser().parse_args(argv)

    cfg = LLMTranslatorConfig(
        model=args.model,
        temperature=args.temperature,
        top_p=args.top_p,
        api_key=args.api_key,
        base_url=args.base_url,
        glossary=args.glossary,
        do_not_translate=args.do_not_translate,
        max_ts_examples=args.max_ts_examples,
    )

    translator = LLMTranslator(cfg)

    translated, total = translator.process_ts_file(
        input_file=args.input_file,
        output_file=args.input_file,  # in-place update, same as previous script
        output_lang=args.output_lang,
        max_entries=args.max_entries,
    )

    print(f"\nProcessed file saved as: {args.input_file}")
    print(f"Total entries translated: {translated}")
    usage = translator.usage_summary()
    print(
        "Token usage — prompt: {prompt}, completion: {completion}, total: {total}".format(
            prompt=usage.get("prompt_tokens", 0),
            completion=usage.get("completion_tokens", 0),
            total=usage.get("total_tokens", 0),
        )
    )
    print(
        "Cache tokens — write: {write}, read: {read}".format(
            write=usage.get("cache_write_tokens", 0),
            read=usage.get("cache_read_tokens", 0),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
