from webapp.utils import nodollar, dollar, avg, hasvalue
from webapp.class8_utils import container_check

import datetime
import numbers

def test_nodollar():
    vals =    [None,  'none',     0,    '',  'None', '0',    ' ', 'anystring', 2, 46, 57.654, 'abc123', '123', 0.00]
    expvals = ['0.00', '0.00', '0.00','0.00','0.00','0.00','0.00','0.00','2.00', '46.00', '57.65', '0.00', '0.00', '0.00']
    for jx, val in enumerate(vals):
        assert nodollar(val) == expvals[jx]

def test_dollar():
    vals =    [None,  'none',     0,    '',  'None', '0',    ' ', 'anystring', 2, 46, 57.654, 'abc123', '123', 0.00]
    expvals = ['$0.00', '$0.00', '$0.00','$0.00','$0.00','$0.00','$0.00','$0.00','$2.00', '$46.00', '$57.65', '$0.00', '$0.00', '$0.00']
    for jx, val in enumerate(vals):
        assert dollar(val) == expvals[jx]

def test_avg():
    vals =    [None,  'none',     0,    '',  'None', '0',    ' ', 'anystring', 2, 46, 57.654, 'abc123', '123', 0.00]
    for val1 in vals:
        for val2 in vals:
            if isinstance(val1,numbers.Number) and isinstance(val2,numbers.Number):
                expval = (val1+val2)/2.0
                assert avg(val1, val2) == expval

def test_hasvalue():
    badvals = [None, 'none', 0, '', 'None', '0', ' ']
    for val in badvals:
        assert hasvalue(val) == 0
    goodvals = ['anystring', 2, 46, 57.654, 'abc123', '123', 0.00]
    for val in goodvals:
        assert hasvalue(val) == 1

def test_container_check():
    goodvals = ['EGHU9330618', 'EITU1205992', 'CAAU5457832', 'ZCSU8465051', 'SUDU6931479']
    for val in goodvals:
        a, b = container_check(val)
        assert a == 0
    badvals = []
    for val in goodvals:
        lastdigit = val[10]
        for ix in range(10):
            if ix != int(lastdigit):
                badvals.append(f'{val[0:10]}{ix}')
    for val in badvals:
        assert len(val) == 11
    for val in badvals:
        a, b = container_check(val)
        assert a == 2




