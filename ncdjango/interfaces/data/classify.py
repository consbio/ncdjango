import numpy


def jenks(data, num_breaks):
    """
    Calculate Jenks natural breaks.

    Adapted from http://danieljlewis.org/files/2010/06/Jenks.pdf
    Credit: Daniel Lewis

    Arguments:
    data -- Array of values to classify.
    num_breaks -- Number of breaks to perform.
    """

    data = numpy.ma.compressed(data)
    if len(data) > 1000:
        data.sort()
        ls = numpy.linspace(0, len(data)-1, 1000)
        ls = [int(round(x)) for x in ls]
        data_list = data[ls]
    else:
        data_list = data

    data_list.sort()

    mat1 = []
    for i in range(0, len(data_list) + 1):
        temp = []
        for j in range(0, num_breaks + 1):
            temp.append(0)
        mat1.append(temp)

    mat2 = []
    for i in range(0, len(data_list) + 1):
        temp = []
        for j in range(0, num_breaks + 1):
            temp.append(0)
        mat2.append(temp)

    for i in range(1, num_breaks + 1):
        mat1[1][i] = 1
        mat2[1][i] = 0
        for j in range(2, len(data_list) + 1):
            mat2[j][i] = float('inf')

    v = 0.0
    for l in range(2, len(data_list) + 1):
        s1 = 0.0
        s2 = 0.0
        w = 0.0
        for m in range(1, l + 1):
            i3 = l - m + 1

            val = float(data_list[i3-1])

            s2 += val * val
            s1 += val

            w += 1
            v = s2 - (s1 * s1) / w
            i4 = i3 - 1

            if i4 != 0:
                for j in range(2, num_breaks + 1):
                    if mat2[l][j] >= (v + mat2[i4][j - 1]):
                        mat1[l][j] = i3
                        mat2[l][j] = v + mat2[i4][j - 1]

        mat1[l][1] = 1
        mat2[l][1] = v

    k = len(data_list)
    kclass = []
    for i in range(0, num_breaks + 1):
        kclass.append(0)

    kclass[num_breaks] = float(data_list[len(data_list) - 1])

    count_num = num_breaks
    while count_num >= 2:
        id = int((mat1[k][count_num]) - 2)

        kclass[count_num - 1] = data_list[id]
        k = int((mat1[k][count_num] - 1))
        count_num -= 1

    return [float(x) for x in kclass][1:]


def quantile(data, num_breaks):
    """
    Calculate quantile breaks.

    Arguments:
    data -- Array of values to classify.
    num_breaks -- Number of breaks to perform.
    """

    def scipy_mquantiles(a, prob=list([.25,.5,.75]), alphap=.4, betap=.4, axis=None, limit=()):
        """ function copied from scipy 0.13.3::scipy.stats.mstats.mquantiles """

        def _quantiles1D(data,m,p):
            x = numpy.sort(data.compressed())
            n = len(x)
            if n == 0:
                return numpy.ma.array(numpy.empty(len(p), dtype=float), mask=True)
            elif n == 1:
                return numpy.ma.array(numpy.resize(x, p.shape), mask=numpy.ma.nomask)
            aleph = (n*p + m)
            k = numpy.floor(aleph.clip(1, n-1)).astype(int)
            gamma = (aleph-k).clip(0,1)
            return (1.-gamma)*x[(k-1).tolist()] + gamma*x[k.tolist()]

        # Initialization & checks ---------
        data = numpy.ma.array(a, copy=False)
        if data.ndim > 2:
            raise TypeError("Array should be 2D at most !")
        #
        if limit:
            condition = (limit[0] < data) & (data < limit[1])
            data[~condition.filled(True)] = numpy.ma.masked
        #
        p =  numpy.array(prob, copy=False, ndmin=1)
        m = alphap + p*(1.-alphap-betap)
        # Computes quantiles along axis (or globally)
        if (axis is None):
            return _quantiles1D(data, m, p)
        return numpy.ma.apply_along_axis(_quantiles1D, axis, data, m, p)

    return scipy_mquantiles(data, numpy.linspace(1.0 / num_breaks, 1, num_breaks))


def equal(data, num_breaks):
    """
    Calculate equal interval breaks.

    Arguments:
    data -- Array of values to classify.
    num_breaks -- Number of breaks to perform.
    """

    step = (numpy.amax(data) - numpy.amin(data)) / num_breaks
    return numpy.linspace(numpy.amin(data) + step, numpy.amax(data), num_breaks)
