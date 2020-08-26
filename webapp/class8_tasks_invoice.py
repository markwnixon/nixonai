from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.pagesizes import landscape
from reportlab.platypus import Image
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth

from webapp.viewfuncs import nonone, nononef, nononestr, dollar, avg, comporname, fullname, address
import csv
import math
import datetime
import shutil
from webapp.CCC_system_setup import addpath, bankdata, scac
import numbers

def writelines(c,fixed_width, thistext, thisfont, thisfontsize, xdist, ydist, lineheight):
    textWidth = stringWidth(thistext, thisfont, thisfontsize)
    if textWidth > fixed_width:
        breaklines = thistext.split()
        newlines = []
        currentline = 0
        newlines.append('')
        for word in breaklines:
            testline = newlines[currentline] + word
            textWidth = stringWidth(testline, thisfont, thisfontsize)
            if textWidth < fixed_width:
                newlines[currentline] = testline + ' '
            else:
                newlines.append(word + ' ')
                currentline = currentline + 1
        for thisline in newlines:
            c.drawString(xdist, ydist, thisline)
            ydist = ydist - lineheight
        ydist = ydist + lineheight
    else:
        c.drawString(xdist, ydist, thistext)

    return xdist, ydist


def make_invo_doc(odata, ldata, pdata1, pdata2, pdata3, cache, invodate, payment, tablesetup, invostyle):

# All dates must begin in datetime format and will be converted to strings as required

    joborder = odata.Jo
    file1 = addpath(f'static/{scac}/data/vinvoice/INV'+joborder+'.pdf')
    file2 = addpath(f'static/{scac}/data/vinvoice/INV'+joborder+'c'+str(cache)+'.pdf')
    today = datetime.datetime.today().strftime('%m/%d/%Y')
    type = joborder[1]
    if invodate is None or invodate == 0:
        invodate = today
    else:
        invodate = invodate.strftime('%m/%d/%Y')

    date1 = odata.Date.strftime('%m/%d/%Y')
    date2 = odata.Date2.strftime('%m/%d/%Y')

    if payment != 0:
        try:
            paydate = payment[2].strftime('%m/%d/%Y')
        except:
            paydate = payment[2]

    # Set numberical formatting values:
    ltm, ctrall, rtm = 36, 310, 575
    dl, hls = 17.6, 530
    m1, m2, m3, m4, m5, m6, m7 = hls - dl, hls - 2 * dl, hls - 3 * dl, hls - 4 * dl, hls - 18 * dl, hls - 23 * dl, hls - 27 * dl
    fulllinesat = [m1, m2, m3, m4, m5, m6, m7]
    dateline = m1+8.2*dl
    p1, p2, p3, p4, p5 = ltm + 87, ltm + 180, ctrall, rtm - 180, rtm - 100
    sds1 = [p1, p2, p3, p4, p5]
    n1, n2, n3, n4 = ltm + 58, ltm + 128, rtm - 140, rtm - 70
    sds2 = [n1, n2, n3, n4]
    q1, q2 = ltm + 180, rtm - 180
    sds3 = [q1, q2]
    bump = 2.5
    tb = bump * 2
    c = canvas.Canvas(file1, pagesize=letter)
    c.setLineWidth(1)

    #Create background logo
    qnote, note, bank, us, lab, logoi = bankdata('FC')
    lab1=lab[0]
    lab2=lab[1]
    logo = logoi[0]
    logo_width = logoi[1]
    logo_height = logoi[2]
    logox = 300 - logo_width / 2.0
    c.drawImage(logo, logox, 670, mask='auto')

    #create background lines
    for i in fulllinesat:
        c.line(ltm, i, rtm, i)

    for l in sds2:
        c.line(l, m3, l, m5)
    for m in sds3:
        c.line(m, m6, m, m7)
    c.line(ltm, m1, ltm, m7)
    c.line(rtm, m1, rtm, m7)
    h1 = avg(m6, m7)-3
    c.line(q2, h1, rtm, h1)

    # Write the document title
    c.setFont('Helvetica-Bold', 24, leading=None)
    c.drawCentredString(rtm-75, dateline+1.5*dl, 'Invoice')

    # Set default font
    c.setFont('Helvetica', 11, leading=None)


    # Date and JO boxes

    c.rect(rtm-150, m1+7*dl, 150, 2*dl, stroke=1, fill=0)
    c.line(rtm-150, dateline, rtm, dateline)
    c.line(rtm-75, m1+7*dl, rtm-75, m1+9*dl)
    c.drawCentredString(rtm-112.5, dateline+bump, 'Date')
    c.drawCentredString(rtm-37.7, dateline+bump, 'Invoice #')

    # Top Boxes (Address boxes)
    ctm = 218
    level1 = m1+5*dl
    header1 = tablesetup['invoicetypes'][invostyle]['Top Blocks']
    lh1 = len(header1)

    if lh1 > 0:
        c.rect(ltm, m1 + dl, 175, 5 * dl, stroke=1, fill=0)
        c.line(ltm, level1, ltm + 175, level1)
        c.drawString(ltm + bump * 3, m1 + 5 * dl + bump * 2, f'{header1[0]}')
        billto = list(range(5))
        if pdata1 is not None:
            billto[0] = comporname(pdata1.Company, fullname(pdata1.First, pdata1.Middle, pdata1.Last))
            billto[1] = nononestr(pdata1.Addr1)
            billto[2] = nononestr(pdata1.Addr2)
            billto[3] = nononestr(pdata1.Telephone)
            # billto[4]=nononestr(pdata1.Email)
            billto[4] = ' '
        else:
            for i in range(5):
                billto[i] = ' '

    if lh1 > 1:
        c.rect(ctm, m1 + dl, 175, 5 * dl, stroke=1, fill=0)
        c.line(ctm, level1, ctm + 175, level1)
        c.drawString(ctm + bump * 3, m1 + 5 * dl + bump * 2, f'{header1[1]}')
        loadat = list(range(5))
        if pdata2 is not None:
            loadat[0] = pdata2.Entity.title()
            loadat[1] = nononestr(pdata2.Addr1).title()
            loadat[2] = nononestr(pdata2.Addr2).title()
            loadat[3] = ''
            loadat[4] = ''
        else:
            for i in range(5):
                loadat[i] = ' '

    if lh1 > 2:
        c.rect(rtm - 175, m1 + dl, 175, 5 * dl, stroke=1, fill=0)
        c.line(rtm - 175, level1, rtm, level1)
        c.drawString(rtm - 170 + bump * 2, m1 + 5 * dl + bump * 2, f'{header1[2]}')
        shipto = list(range(5))
        if pdata3 is not None:
            shipto[0] = pdata3.Entity.title()
            shipto[1] = nononestr(pdata3.Addr1).title()
            shipto[2] = nononestr(pdata3.Addr2).title()
            shipto[3] = ''
            shipto[4] = ''
        else:
            for i in range(5):
                shipto[i] = ' '


    #Create the middle row headers and auto fit the width for the items

    header_font = 'Helvetica'
    header_fontsize = 11
    headerval_font = 'Helvetica'
    headerval_fontsize = 9
    header2 = tablesetup['invoicetypes'][invostyle]['Middle Blocks']
    header2items = tablesetup['invoicetypes'][invostyle]['Middle Items']
    lh2 = len(header2)
    header2_value = []
    maxw = []


    for ix, header in enumerate(header2items):
        thisvalue = getattr(odata,header)
        if thisvalue is None: thisvalue = ''
        if isinstance(thisvalue, numbers.Number):
            thisvalue = str(thisvalue)
        elif isinstance(thisvalue, datetime.date):
            thisvalue = thisvalue.strftime('%m/%d/%Y')
        header_width = stringWidth(header, header_font, header_fontsize)
        headerval_width = stringWidth(thisvalue, headerval_font, headerval_fontsize)
        maxval = max(header_width,headerval_width)
        header2_value.append(thisvalue)
        maxw.append(maxval)

    print('maxw=',maxw)
    total_width = rtm - ltm
    total_need = sum(maxw)
    allocation = []
    thislft = ltm
    newctr = []
    newlft = []
    for each in maxw:
        thisw = each * total_width/total_need
        allocation.append(thisw)
        newctr.append(thislft+thisw/2)
        thislft = thislft + thisw
        newlft.append(thislft)

    print('allocation newctr',allocation,newctr)
    ctr = [avg(ltm, p1), avg(p1, p2), avg(p2, p3), avg(p3, p4), avg(p4, p5), avg(p5, rtm)]
    for jx, header in enumerate(header2):
        c.drawCentredString(newctr[jx], m2+tb, header)
    c.setFont('Helvetica', 9, leading=None)
    for jx, header in enumerate(header2_value):
        c.drawCentredString(newctr[jx], m3+tb, nononestr(header))
    for lft in newlft:
        c.line(lft, m1, lft, m3)

    # Create the lower row headers
    header3 = tablesetup['invoicetypes'][invostyle]['Lower Blocks']
    ctr = [avg(ltm, n1), avg(n1, n2), avg(n2, n3), avg(n3, n4), avg(n4, rtm)]
    for j, i in enumerate(header3):
        c.drawCentredString(ctr[j], m4+tb, i)


    dh = 12
    ct = 305

    top = m6-1.5*dh
    for i in bank:
        c.drawCentredString(ct, top, i)
        top = top-dh

    top = m1+9*dl-5
    for i in us:
        c.drawString(ltm+bump, top, i)
        top = top-dh

    bottomline = m6-23
    c.setFont('Helvetica-Bold', 12, leading=None)
    c.drawString(q2+tb, bottomline, 'Balance Due:')

    c.setFont('Helvetica', 10, leading=None)
    c.drawCentredString(avg(q2, rtm), m7+12, 'Add $39.00 for all international wires')

    c.setFont('Times-Roman', 9, leading=None)
    j = 0
    dh = 9.95
    top = m5-dh
    for i in note:
        c.drawString(ltm+tb, top, note[j])
        j = j+1
        top = top-dh


# _______________________________________________________________________
    # Insert data here
# _______________________________________________________________________

    c.setFont('Helvetica', 10, leading=None)

    if type == 'T':
        dh = 13
        top = level1-dh
        lft = ltm+bump*3
        for i in billto:
            c.drawString(lft, top, i)
            top = top-dh

        top = level1-dh
        lft = ctm+bump*3
        for i in loadat:
            c.drawString(lft, top, i)
            top = top-dh

        top = level1-dh
        lft = rtm-175+bump*3
        for i in shipto:
            c.drawString(lft, top, i)
            top = top-dh

    x = avg(rtm-75, rtm)
    y = dateline-dh-bump
    c.drawCentredString(x, y, joborder)
    x = avg(rtm-75, rtm-150)
    c.drawCentredString(x, y, invodate)



    total = 0
    top = m4-dh
    for data in ldata:
        qty = float(float(data.Qty))
        each = float(float(data.Ea))
        subtotal = qty*each
        total = total+subtotal
        line4 = [str(qty), data.Service]
        line5 = nononestr(data.Description)
        line6 = [each, subtotal]

        j = 0
        for i in line4:
            ctr = [avg(ltm, n1), avg(n1, n2)]
            c.drawCentredString(ctr[j], top, i)
            j = j+1

        xdist, top = writelines(c, 260, line5, 'Helvetica', 9, n2 + tb, top, dh)

        j = 0
        for i in line6:
            ctr = [n4-tb*2, rtm-tb*2]
            c.drawRightString(ctr[j], top, dollar(i))
            j = j+1
        top = top-1.5*dh

    if payment != 0:
        c.setFont('Helvetica-Bold', 18, leading=None)
        c.drawCentredString(ct, top-2*dh, 'Payment Received')

    if payment != 0:
        c.setFont('Helvetica-Bold', 12, leading=None)
        try:
            thispay = float(payment[0])
        except:
            thispay = 0.00
        top = top-4*dh
        try:
            c.drawString(n2+bump, top, 'Your payment of '+payment[0]+', Ref No. '+payment[1])
        except:
            c.drawString(ct, top, 'There is no payment data as of yet')
        try:
            c.drawString(n2+bump, top-dh, 'was applied on ' + paydate)
        except:
            c.drawString(ct, top-dh, 'There is a problem with the date')
    else:
        thispay = 0.00

    total = total-thispay

    c.drawRightString(rtm-tb*2, bottomline, dollar(total))

    c.showPage()
    c.save()
    #
    # Now make a cache copy
    shutil.copy(file1, file2)

    return file2