import numpy as np
import scipy.interpolate
import scipy.ndimage


def rebin(counts, oldEnergies, newEcal):
    """
    Rebins a list ouf counts to a new energy calibration.

    :param counts:      numpy array ouf counts indexed by channel
    :param oldEnergies: numpy array of energies indexed by channel
    :param newEcal:     list of new energy polynomial coefficents to rebin to: [E3 E2 E1 E0]
    :return:            numpy array of rebinned counts
    """
    newEnergies = np.polyval(np.flip(newEcal), np.arange(len(counts)+1))
    newCounts   = np.zeros(len(counts))

    # move old energies index to first value greater than the first value in newEnergies
    oe = 0 # will always lead ne in energy boundary value
    while oe < len(oldEnergies) and oldEnergies[oe] <= newEnergies[0]: oe += 1
    ne0 = 0
    while newEnergies[ne0] <= oldEnergies[oe]:
        ne0 += 1

    # loop through and distribute old counts into new bins
    for ne in range(ne0, len(newCounts)):
        if oe == len(oldEnergies): break  # have already distributed all old counts

        # if no old energy boundaries within this new bin, new bin is fraction of old bin
        if oldEnergies[oe] > newEnergies[ne + 1]:
            newCounts[ne] = counts[oe - 1] * (newEnergies[ne + 1] - newEnergies[ne]) \
                            / (oldEnergies[oe] - oldEnergies[oe - 1])

        # else there are old energy boundaries in this new bin: add each portion of old bins
        else:
            # Step 1: add first partial(or full) old bin
            # TODO: This will crash if (oldEnergies[oe] - oldEnergies[oe-1]) < 0; might be necessary to handle this?
            newCounts[ne] = counts[oe-1] * (oldEnergies[oe] - newEnergies[ne]) \
                            / (oldEnergies[oe] - oldEnergies[oe-1])
            oe += 1

            # Step 2: add middle full old bins
            while oe < len(oldEnergies) and oldEnergies[oe] <= newEnergies[ne+1]:
                newCounts[ne] += counts[oe-1]
                oe += 1
            if oe == len(oldEnergies): break

            # Step 3: add last partial old bin
            newCounts[ne] += counts[oe-1] * (newEnergies[ne+1] - oldEnergies[oe-1]) \
                             / (oldEnergies[oe] - oldEnergies[oe-1])
    return newCounts


def integral_rebin(a, old_range, newdim, new_range, highnoise=0, sample_highnoise=False):
    a_integral = np.concatenate(([0.,],np.cumsum(a)))
    a_points = np.linspace(start=old_range[0],stop=old_range[1],num=len(a)+1, endpoint=True)
    out_points = (np.linspace(start=new_range[0], stop=new_range[1], num=newdim + 1, endpoint=True))
    if highnoise:
        assert(highnoise>0)
        if sample_highnoise:
            extra_points = out_points[out_points>a_points[-1]]
            a_points= np.concatenate((a_points,extra_points))
            bin_expectation = highnoise/len(extra_points)
            noise_bins = np.random.poisson(bin_expectation,len(extra_points))
            noise_int = np.cumsum(noise_bins)+a_integral[-1]
            a_integral = np.concatenate((a_integral,noise_int))
        else:
            a_points=np.append(a_points,out_points[-1])
            a_integral= np.append(a_integral,a_integral[-1]+highnoise)
    interp = np.interp(x=out_points,xp=a_points,fp=a_integral)
    return np.rint(np.diff(interp)).astype(int)




def congrid(a, newdims, method='linear', centre=False, minusone=False):
    '''
    https://scipy-cookbook.readthedocs.io/items/Rebinning.html
    Arbitrary resampling of source array to new dimension sizes.
    Currently only supports maintaining the same number of dimensions.
    To use 1-D arrays, first promote them to shape (x,1).

    Uses the same parameters and creates the same co-ordinate lookup points
    as IDL''s congrid routine, which apparently originally came from a VAX/VMS
    routine of the same name.

    method:
    neighbour - closest value from original data
    nearest and linear - uses n x 1-D interpolations using
                         scipy.interpolate.interp1d
    (see Numerical Recipes for validity of use of n 1-D interpolations)
    spline - uses ndimage.map_coordinates

    centre:
    True - interpolation points are at the centres of the bins
    False - points are at the front edge of the bin

    minusone:
    For example- inarray.shape = (i,j) & new dimensions = (x,y)
    False - inarray is resampled by factors of (i/x) * (j/y)
    True - inarray is resampled by(i-1)/(x-1) * (j-1)/(y-1)
    This prevents extrapolation one element beyond bounds of input array.
    '''
    if not a.dtype in [np.float64, np.float32]:
        a = np.cast[float](a)

    m1 = np.cast[int](minusone)
    ofs = np.cast[int](centre) * 0.5
    old = np.array(a.shape)
    ndims = len(a.shape)
    if len(newdims) != ndims:
        print('''
        [congrid] dimensions error. 
        This routine currently only support 
        rebinning to the same number of dimensions''')
        return None
    newdims = np.asarray(newdims, dtype=float)
    dimlist = []

    if method == 'neighbour':
        for i in range(ndims):
            base = np.indices(newdims)[i]
            dimlist.append((old[i] - m1) / (newdims[i] - m1) \
                           * (base + ofs) - ofs)
        cd = np.array(dimlist).round().astype(int)
        newa = a[list(cd)]
        return newa

    elif method in ['nearest', 'linear']:
        # calculate new dims
        for i in range(ndims):
            base = np.arange(newdims[i])
            dimlist.append((old[i] - m1) / (newdims[i] - m1) \
                           * (base + ofs) - ofs)
        # specify old dims
        olddims = [np.arange(i, dtype=np.float) for i in list(a.shape)]

        # first interpolation - for ndims = any
        mint = scipy.interpolate.interp1d(olddims[-1], a, kind=method)
        newa = mint(dimlist[-1])

        trorder = [ndims - 1] + list(range(ndims - 1))
        for i in range(ndims - 2, -1, -1):
            newa = newa.transpose(trorder)

            mint = scipy.interpolate.interp1d(olddims[i], newa, kind=method)
            newa = mint(dimlist[i])

        if ndims > 1:
            # need one more transpose to return to original dimensions
            newa = newa.transpose(trorder)

        return newa
    elif method in ['spline']:
        oslices = [slice(0, j) for j in old]
        oldcoords = np.ogrid[oslices]
        nslices = [slice(0, j) for j in list(newdims)]
        newcoords = np.mgrid[nslices]

        newcoords_dims = range(np.rank(newcoords))
        # make first index last
        newcoords_dims.append(newcoords_dims.pop(0))
        newcoords_tr = newcoords.transpose(newcoords_dims)
        # makes a view that affects newcoords

        newcoords_tr += ofs

        deltas = (np.asarray(old) - m1) / (newdims - m1)
        newcoords_tr *= deltas

        newcoords_tr -= ofs

        newa = scipy.ndimage.map_coordinates(a, newcoords)
        return newa
    else:
        print('Congrid error: Unrecognized interpolation type. Currently only "neighbour", "nearest", "linear", '
              'and "spline" are supported.')
        return None