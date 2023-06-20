from webapp import db
from webapp.models import Income, Openi

def intdol(int):
    if int is not None:
        fd = int/100
        return "${:0,.2f}".format(fd)
    else:
        return ''

def get_revenues():
    #title1,col1,data1,title2,col2,data2 = revenues()
    data1 = []
    data2 = []
    idata = Income.query.all()
    odata = Openi.query.all()
    title1 = idata[0].Description
    title2 = odata[0].Description
    col1 = ['Month', 'Monthly Revenue', 'Cumulative', 'Collected', 'Open Invoices']
    col2 = ['Company', 'Over 30 Days', 'Under 30 Days', 'Total Open Invoices']
    for idat in idata:
        data1.append([idat.Month, intdol(idat.Mrev), intdol(idat.Crev), intdol(idat.Revcoll), intdol(idat.Open)])
    for odat in odata:
        data2.append([odat.Company, intdol(odat.Over30), intdol(odat.Under30), intdol(odat.Total)])
    return title1, col1, data1, title2, col2, data2