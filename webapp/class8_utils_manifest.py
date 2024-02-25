from flask import request
from webapp.models import People, Drops, Drivers, Vehicles, Orders
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.pdfmetrics import stringWidth
import datetime
import shutil
import os
from webapp.viewfuncs import parseline, parselinenoupper
from webapp.CCC_system_setup import addpath, bankdata, scac
from webapp.class8_utils_invoice import scroll_write, center_write, write_lines
from webapp.utils import *
from webapp.class8_utils_invoice import make_topline_headers


def manfile(joborder, cache):
    if not hasinput(cache): cache = 1
    wpath=addpath(f'static/{scac}/data/vManifest/Manifest')
    file1=wpath+joborder+'.pdf'
    file2=wpath+joborder+'c'+str(cache)+'.pdf'
    file3 = f'static/{scac}/data/vManifest/Manifest'+joborder+'c'+str(cache)+'.pdf'
    file4 = wpath + joborder + 'c' + str(cache - 1) + '.pdf'
    try:
        os.remove(file4)
    except:
        pass
        #print(f'No file {file4} found')
    return file1, file2, file3

def minbox_write(header, lineitems, fs1, fs2):
    eachwidth = []
    header = text_ready(header)
    eachwidth.append(stringWidth(header, 'Helvetica', fs1))
    for line in lineitems:
        line = text_ready(line)
        eachwidth.append(stringWidth(line, 'Helvetica', fs2))
    return max(eachwidth)

def get_padding(sectors, sectorlines, fs1, fs2, margin, ltm, rtm):
    total_width = rtm - ltm
    boxwidth = []
    for jx, sector in enumerate(sectors):
        eachwidth = []
        sector = text_ready(sector)
        eachwidth.append(stringWidth(sector, 'Helvetica', fs1))
        lineitems = sectorlines[jx]
        for line in lineitems:
            line = text_ready(line)
            eachwidth.append(stringWidth(line, 'Helvetica', fs2))
        boxwidth.append(max(eachwidth)+2*margin)
    total_need = sum(boxwidth)
    space_available = total_width - total_need
    lt = len(sectors) - 1
    padding = space_available/lt
    #print(f'The calculated dimensions for sector padding are: total_width: {total_width}, total_need: {total_need}, space_available: {space_available}, padding: {padding}')
    return padding

def get_shipper(odat):
    shipper = odat.Shipper
    bid = int(odat.Bid)
    if bid != 0:
        try:
            bid = int(odat.Bid)
            #print(shipper,bid)
            pdat = People.query.get(bid)
            return [pdat.Company, pdat.Addr1, pdat.Addr2, pdat.Telephone, '']
        except:
            #print(shipper)
            pdat = People.query.filter(People.Company == shipper).first()
            #print(pdat.Company)
    else:
        pdat = People.query.filter(People.Company == shipper).first()
    if pdat is not None:
        return [pdat.Company, pdat.Addr1, pdat.Addr2, pdat.Telephone, '']
    else:
        return ['']*5

def get_sectors(ht, odat):
    dates = [odat.Date.strftime('%m/%d/%Y'), odat.Date2.strftime('%m/%d/%Y'), odat.Date2.strftime('%m/%d/%Y')]
    sectors = ['Pickup Load at Port', 'Deliver To', 'Return to Port']
    sectorlocs = [['']*5,['']*5,['']*5,['']*5]
    sectorlocs[0] = get_shipper(odat)


    truck = odat.Truck
    tdata = Vehicles.query.filter(Vehicles.Unit == truck).first()
    if tdata is None:
        tdata = Vehicles.query.filter(Vehicles.id >= 1).first()
    truck = str(tdata.Unit)
    tag = str(tdata.Plate)
    middle1 = ['SCAC', 'Driver', 'Truck #', 'Tag #', 'Booking', 'Container', 'Size/Type', 'Seal']
    middle1data = [scac, odat.Driver, truck, tag, odat.Release, odat.Container, odat.Type, odat.Seal]

    order=str(odat.Order)
    pickup=str(odat.Pickup)
    date1=odat.Date
    date2=odat.Date3
    type=odat.Type

    try:
        date1s=date1.strftime('%m/%d/%Y')
    except:
        date1s='Nodate'
    try:
        date2s=date2.strftime('%m/%d/%Y')
    except:
        date2s='Nodate'

    loaddatetime=date1s
    deliverdatetime=date2s

    middle2 = ['Order', 'Pickup/ShipperID', 'Gate Out', 'Delivery']
    middle2data = [order, pickup, loaddatetime, deliverdatetime]

    if hasvalue(ht):
        #print(f'ht here is {ht}')

        if 'Import' in ht:
            sectors = ['Pickup Load at Port', 'Deliver To', 'Return to Port']
            sectorlocs[1] = odat.Dropblock1.splitlines()
            sectorlocs[2] = odat.Dropblock2.splitlines()
            sectorlocs[3] = odat.Dropblock1.splitlines()
            middle1 = ['SCAC','Driver', 'Truck #', 'Tag #', 'BOL', 'Container' ,'Size/Type', 'Chassis']
            middle1data = [scac,odat.Driver,truck,tag,odat.Booking,odat.Container,odat.Type,odat.Chassis]

        elif 'Export' in ht:
            sectors = ['Pickup Empty at Port', 'Load At', 'Return to Port']
            sectorlocs[1] = odat.Dropblock1.splitlines()
            sectorlocs[2] = odat.Dropblock2.splitlines()
            sectorlocs[3] = odat.Dropblock1.splitlines()
            middle1 = ['SCAC','Driver', 'Truck #', 'Tag #', 'Booking', 'Container' ,'Size/Type', 'Chassis']
            middle1data = [scac,odat.Driver,truck,tag,odat.Booking,odat.Container,odat.Type,odat.Chassis]

        elif 'OTR' in ht:
            sectors = ['Pickup Location', 'Delivery Location']
            sectorlocs[1] = odat.Dropblock1.splitlines()
            sectorlocs[2] = odat.Dropblock2.splitlines()
            sectorlocs[3] = odat.Dropblock1.splitlines()
            middle1 = ['SCAC','Driver', 'Truck #', 'Tag #', 'Trailer #','Size/Type', 'Seal']
            middle1data = [scac,odat.Driver,truck,tag,odat.Container,odat.Type,odat.Seal]

        elif ht == 'Dray-Transload-Deliver':
            sectors = ['Pickup Load at Port', 'Transload At', 'Deliver To']
            sectorlocs[1] = odat.Dropblock1.splitlines()
            sectorlocs[2] = odat.Dropblock2.splitlines()
            sectorlocs[3] = odat.Dropblock3.splitlines()
            middle1 = ['SCAC','Driver', 'Truck #', 'Tag #', 'Trailer #','Size/Type', 'Seal']
            middle1data = [scac,odat.Driver,truck,tag,odat.Container,odat.Type,odat.Seal]

    sectors = ['Shipper/Agent'] + sectors
    return sectors, sectorlocs, dates, middle1, middle1data, middle2, middle2data

def center_write_items(headers, headeritems, fs1, fs2, ltm, rtm):
    total_width = rtm - ltm
    maxw = []
    # headeritems are the header data
    # headers are the labels for the column data to be shown on the invoice
    #print(headeritems)
    for ix, item in enumerate(headeritems):
        header_width = stringWidth(headers[ix], 'Helvetica', fs1)
        #if item is None: item = ''
        if not isinstance(item, str): item = ''
        #print(f'The item is {item}')
        headerval_width = stringWidth(item, 'Helvetica', fs2)
        maxval = max(header_width, headerval_width)
        # Store the max lengths in a list
        maxw.append(maxval)

    total_need = sum(maxw)
    newctr, newlft = [], []
    thislft = ltm
    for each in maxw:
        thisw = each * total_width / total_need
        newctr.append(thislft + thisw / 2)
        thislft = thislft + thisw
        newlft.append(thislft)

    return newctr, newlft

def catline(instring,j):
    if len(instring)>j:
        instring=instring[0:j-1]
    return instring

def avg(in1,in2):
    out=(in1+in2)/2
    return out

def comporname(company,name):
    if company is None or company=='':
        nameout=name
    else:
        if len(company)<3:
            nameout=name
        else:
            nameout=company
    return nameout

def fullname(first,middle,last):
    if first is not None:
        nameout=first
    else:
        nameout=''
    if middle is not None:
        nameout=nameout+' '+middle
    if last is not None:
        nameout=nameout+' '+last
    if len(nameout)>55:
        nameout=first + ' ' + last
    return nameout

def address(addr1,addr2,addr3):
    street=addr1
    if addr3 is None or addr3=='':
        cityst=addr2
    else:
        if len(addr3)<5:
            cityst=addr2
    if addr2 is None or addr2=='':
        cityst=addr3
        if len(addr2)<3:
            cityst=addr3
    if addr2 and addr3:
        if len(addr2)>3 and len(addr3)>3:
            street=addr1 + ' ' + addr2
            cityst=addr3
    return street,cityst

def nononestr(input):
    if input is None or input=='None':
        input=''
    return input

def nonone(input):
    if input is None:
        input=0
    return input



def makemanifest(odat, tablesetup):
    # All dates must begin in datetime format and will be converted to strings as required

    joborder = odat.Jo
    cache = odat.Mcache
    file1, file2 ,file3 = manfile(joborder,cache)
    today = datetime.datetime.today().strftime('%m/%d/%Y')

    ltm, ctrall, rtm = 36, 310, 575
    dl, hls = 17.6, 500
    m1, m2, m3, m4, m5, m6, m7, m8, m9, m10 = hls - dl, hls - 2 * dl, hls - 3 * dl, hls - 4 * dl, hls - 5 * dl, hls - 6 * dl, hls - 7 * dl, hls - 18 * dl, hls - 23 * dl, hls - 27 * dl
    bump = 2.5
    tb = bump * 2
    dh = 12
    ct = 305
    c = canvas.Canvas(file1, pagesize=letter)
    c.setLineWidth(1)
    t1 = 765
    t2 = 735
    # Draw the ltm and rtm vertical lines
    c.line(ltm,t1,ltm,m10)
    c.line(rtm,t1,rtm,m10)
    # Draw the bottom horizontal line
    c.line(ltm, m10, rtm, m10)

    #Create background logo
    qnote, note, bank, us, lab, logoi = bankdata('FC')
    lab1=lab[0]
    lab2=lab[1]
    logo = logoi[0]
    logo_width = logoi[1]
    logo_height = logoi[2]
    logox = 300 - logo_width / 2.0
    c.drawImage(logo, logox, logoi[3], mask='auto')

    #Title block
    c.setLineWidth(1.5)
    c.rect(rtm,t2,ltm-rtm,30,stroke=1,fill=0)
    c.setFont('Helvetica-Bold',24,leading=None)
    c.drawCentredString(avg(rtm,ltm),t2+8,'Straight Bill of Lading')

    #Company Salutation
    c.setFont('Helvetica-Bold', 12, leading=None)
    top = m1 + 9 * dl
    for u in us:
        c.drawString(ltm+3*bump,top,u)
        top=top-dh

    # Date and JO boxes

    try:
        sigdate = odat.Date3
        sigdate = sigdate.strftime('%m/%d/%Y')
    except:
        sigdate=today

    dateline = m1 + 8.2 * dl
    c.setFont('Helvetica', 11, leading=None)
    c.rect(rtm-150, m1+7*dl, 150, 2*dl, stroke=1, fill=0)
    c.line(rtm-150, dateline, rtm, dateline)
    c.line(rtm-75, m1+7*dl, rtm-75, m1+9*dl)
    c.drawCentredString(rtm-112.5, dateline+bump, 'Date')
    c.drawCentredString(rtm-37.7, dateline+bump, 'Job Order')
    x = avg(rtm - 75, rtm)
    y = dateline - dh - bump
    c.setFont('Helvetica', 10, leading=None)
    c.drawCentredString(x, y, joborder)
    x = avg(rtm - 75, rtm - 150)
    c.drawCentredString(x, y, sigdate)

    # Top Boxes (Address boxes)
    haul_type = request.values.get('HaulType')
    if haul_type is None:
        haul_type = odat.HaulType

    # Get the sector labels/data for the haul type chosen:
    sectors, sectorlines, dates, middle1, middle1data, middle2, middle2data = get_sectors(haul_type, odat)

    if 1 == 2:
        # Calculate horizonal space requirements and perform best fit
        padding = -1
        iter = 1
        fs1 = 11
        fs2 = 10
        while padding < 0 and iter < 8:
            padding = get_padding(sectors, sectorlines, fs1, fs2, 3*bump, ltm, rtm)
            if padding < 0:
                fs1 = fs1 - .25
                fs2 = fs2 - .25
                iter = iter + 1

        c.setFont('Helvetica', fs1, leading=None)
        level1 = m1 + 5 * dl
        leftstart = ltm
        for jx, sector in enumerate(sectors):

            lineitems = sectorlines[jx]
            width_need = minbox_write(sector, lineitems, fs1, fs2)

            boxwidth = bump*3+width_need+bump*3

            c.rect(leftstart, m1 + dl, boxwidth , 5 * dl, stroke=1, fill=0)
            c.line(leftstart, level1, leftstart+boxwidth , level1)

            c.drawString(leftstart + bump * 3, m1 + 5 * dl + bump * 2, sector)
            #print('lineitems', lineitems)
            top = scroll_write(c, 'Helvetica', fs2, level1 - dh, leftstart + bump * 3, 13, lineitems, 175)
            leftstart = leftstart + boxwidth + padding

    ctm = 218
    level1 = m1+5*dl
    pdata1 = People.query.filter(People.id == odat.Bid).first()
    make_topline_headers(c, tablesetup, pdata1, odat, odat.HaulType, ltm, m1, dl, bump, ctm, rtm, level1, dh)

    # Middle Boxes Top Level
    full_lines = [hls - .5*dl, hls-1.5*dl, hls - 2.5 * dl]
    for full_line in full_lines: c.line(ltm,full_line,rtm,full_line)
    thisctr, thislft = center_write_items(middle1, middle1data, 11, 9, ltm, rtm)
    c.setFont('Helvetica', 11, leading=None)
    for jx, header in enumerate(middle1):
        c.drawCentredString(thisctr[jx], full_lines[1] + tb, header)
    c.setFont('Helvetica', 9, leading=None)
    for jx, header in enumerate(middle1data):
        if not isinstance(header, str): header = ''
        c.drawCentredString(thisctr[jx], full_lines[2] + tb, nononestr(header))
    for lft in thislft:
        c.line(lft, full_lines[0], lft, full_lines[2])

    #Middle Boxes Lower Level
    full_lines = [hls - 3 * dl, hls - 4 * dl, hls - 5 * dl]
    for full_line in full_lines: c.line(ltm,full_line,rtm,full_line)
    thisctr, thislft = center_write_items(middle2, middle2data, 11, 9, ltm, rtm)
    c.setFont('Helvetica', 11, leading=None)
    for jx, header in enumerate(middle2):
        c.drawCentredString(thisctr[jx], full_lines[1] + tb, header)
    c.setFont('Helvetica', 9, leading=None)
    for jx, header in enumerate(middle2data):
        c.drawCentredString(thisctr[jx], full_lines[2] + tb, nononestr(header))
    for lft in thislft:
        c.line(lft, full_lines[0], lft, full_lines[2])

    # Commodity and Packaging Section
    full_lines = [hls - 5.5 * dl, hls - 6.5 * dl, hls - 7.5 * dl]
    for full_line in full_lines: c.line(ltm,full_line,rtm,full_line)
    commodity = odat.Commodity
    packing = odat.Packing
    commodityheader=['Commodity and Units', 'Packaging and Description']
    commoditylines=[str(commodity), str(packing)]
    c.setFont('Helvetica',10,leading=None)
    ctr=[avg(ltm,ctrall),avg(ctrall,rtm)]
    for jx, comline in enumerate(commodityheader):
        c.drawCentredString(ctr[jx],full_lines[1]+tb,comline)
        c.drawCentredString(ctr[jx],full_lines[2]+tb,commoditylines[jx])
    c.line(ctrall,full_lines[0],ctrall,full_lines[2])

    #Special Instructions Section
    desclines = odat.Description
    if desclines is None: desclines = 'No description provided'
    full_lines = [hls - 8 * dl, hls - 14 * dl]
    for full_line in full_lines: c.line(ltm,full_line,rtm,full_line)

    top = full_lines[0] - dl
    c.setFont('Helvetica-Bold',10,leading=None)
    c.drawString(40,top,'Special Instructions:')
    top=top-dl
    for desc in desclines.splitlines():
        c.drawString(40,top,desc)
        top = top - dl

    #Signature and Date/Arrival/Depart Section
    full_lines = [hls - 14 * dl, hls - 20* dl]
    for full_line in full_lines: c.line(ltm, full_line, rtm, full_line)
    c.setFont('Helvetica',11,leading=None)
    x=ctrall+110
    top = full_lines[0] - dl
    c.drawRightString(x,top,'Date:')
    c.drawString(x+20, top+bump, sigdate)
    c.line(x+4,top,x+150,top)

    top=top-dl*1.5
    c.drawRightString(x,top,'   Arrival Time:')
    c.line(x+4,top,x+150,top)
    top=top-dl*1.5
    c.drawRightString(x,top,'Depart Time:')
    c.line(x+4,top,x+150,top)

    x=ltm+5
    c.drawString(x,top,'Received By:')
    c.line(x + 75, top, ctrall + 35, top)

    #Driver Notes Section
    c.setFont('Helvetica-Bold', 10, leading=None)
    note=list(range(4))
    note[0]='All appointments must be met.  If late the load may be refused or worked in without detention.'
    note[1]='If shipper and receiver addresses do not match BOL contact office immediately'
    note[2]='Dates for arrivals and departures are local.'
    note[3]='Dates, times, and estimates are given without any guarantee and are subject to change without prior notice.'
    dh=12
    full_lines = [hls - 20 * dl, hls - 24* dl]
    for full_line in full_lines: c.line(ltm, full_line, rtm, full_line)

    top=full_lines[0] - dl
    c.drawString(ltm+tb,top,'Driver Notes:')
    c.setFont('Helvetica',10,leading=None)
    top=top-dh
    for nline in note:
        c.drawString(ltm+tb,top,nline)
        top=top-dh

#___________________________________________________________



    cache = odat.Mcache
    if cache is None:
        cache = 0










    c.showPage()
    c.save()
    #
    #Now make a cache copy
    shutil.copy(file1,file2)
    try:
        os.remove(file1)
    except:
        pass
    #print('returning file',file3)
    return file3
