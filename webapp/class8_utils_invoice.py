from webapp import db
from webapp.models import Bills, People
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.pagesizes import landscape
from reportlab.platypus import Image
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.graphics.barcode import eanbc, qr, usps

from reportlab.lib.utils import simpleSplit
from webapp.page_merger import pagemerger
from PIL import Image

from webapp.viewfuncs import nonone, nononef, nononestr, dollar, avg, comporname, fullname, address
import csv
import math
import datetime
import shutil
from webapp.CCC_system_setup import addpath, bankdata, scac
import numbers
from webapp.utils import *
from webapp.class8_utils import *

def truncate_item(item,lena, fs):
    item_width = stringWidth(item, 'Helvetica', fs)
    #print(f'item width {item_width} versus limit {lena}')
    if item_width > lena:
        while item_width > lena:
            item = item.rpartition(' ')[0]
            item_width = stringWidth(item, 'Helvetica', fs)
            #print(f'new item width {item_width}')
    return item


def scroll_write(c, fonttype, fontsize, top, left, dsp, itemlist, available_space):
    c.setFont(fonttype, fontsize, leading=None)
    for item in itemlist:
        # text_ready just makes sure the item is a string
        item = text_ready(item)
        # truncate_item truncates the item if it is longer than the available space
        item = truncate_item(item,available_space,fontsize)
        c.drawString(left, top, item)
        top = top - dsp
    return top

def center_write(odata, headers, headeritems, fs1, fs2, ltm, rtm):
    total_width = rtm - ltm
    header_values, maxw = [], []
    # headeritems are the database column names where values are stored
    # headers are the labels for the column data to be shown on the invoice
    for ix, item in enumerate(headeritems):
        thisvalue = getattr(odata, item)
        if thisvalue is None: thisvalue = ''
        if isinstance(thisvalue, numbers.Number):
            thisvalue = str(thisvalue)
        elif isinstance(thisvalue, datetime.date):
            thisvalue = thisvalue.strftime('%m/%d/%Y')
        header_width = stringWidth(headers[ix], 'Helvetica', fs1)
        headerval_width = stringWidth(thisvalue, 'Helvetica', fs2)
        maxval = max(header_width, headerval_width)
        # Store the values and their lengths in a list
        header_values.append(thisvalue)
        maxw.append(maxval)

    total_need = sum(maxw)
    newctr, newlft = [], []
    thislft = ltm
    for each in maxw:
        thisw = each * total_width / total_need
        newctr.append(thislft + thisw / 2)
        thislft = thislft + thisw
        newlft.append(thislft)

    return newctr, newlft, header_values

def write_lines(c,fixed_width, thistext, thisfont, thisfontsize, xdist, ydist, lineheight):

    lines = simpleSplit(thistext, thisfont, thisfontsize, fixed_width)
    #print(lines)
    #print(f'lines are {lines}')
    for thisline in lines:
        c.drawString(xdist, ydist, thisline)
        ydist = ydist - lineheight
    if lines != []: ydist = ydist + lineheight

    return xdist, ydist

def opto_table(c, headers, rows, font, fontsize, ltm, rtm, mtop, mbot, max_block, headerbold, hlineson, vlineson):
    fontbold = f'{font}-Bold'
    hlen = len(headers)
    spread = 15
    min_w = []
    for header in headers:
        if headerbold: thisw = stringWidth(header, fontbold, fontsize)
        else: thisw = stringWidth(header, font, fontsize)
        #print(f'header {header} {thisw}')
        thisw = thisw + spread
        min_w.append(thisw)
    for row in rows:
        for kx, col in enumerate(row):
            if not hasvalue(col): col = ''
            #print(f'col is {col} and font is {font}')
            thisw = stringWidth(col, font, fontsize) + spread
            thatw = min_w[kx]
            new_min = max(thisw, thatw)
            min_w[kx] = new_min
    min_w[max_block] = 0
    total_spread = sum(min_w)
    width_avail = rtm - ltm
    mx_len = width_avail - total_spread
    min_w[max_block] = mx_len
    #print(f'Here are the widths: {min_w}')
    ctrx = []
    sdsx = []
    thisctr = ltm
    thisend = ltm
    for ix, header in enumerate(headers):
        if ix < hlen:
            thisctr = thisend + min_w[ix] / 2
            thisend = thisend + min_w[ix]
        ctrx.append(thisctr)
        sdsx.append(thisend)

    nlines = len(rows) + 1
    m_per_line = (mtop - mbot)/nlines
    extra_ht = m_per_line - fontsize*.8
    bump = extra_ht/2
    m_here = mtop - m_per_line + bump
    #print(f'Using mtop {mtop}, mbot {mbot}, m_per {m_per_line}, extra_ht {extra_ht}, bump {bump}')

    if hlineson: c.line(ltm, mtop, rtm, mtop)
    if headerbold: c.setFont(fontbold, fontsize, leading=None)
    for jx, header in enumerate(headers):
        if hlineson: c.line(ltm, m_here - bump, rtm, m_here - bump)
        c.drawCentredString(ctrx[jx], m_here, header)

    c.setFont(font, fontsize, leading=None)
    for row in rows:
        m_here = m_here - m_per_line
        if hlineson: c.line(ltm, m_here-bump, rtm, m_here-bump)
        for jx, col in enumerate(row):
            if not hasvalue(col): col = ''
            c.drawCentredString(ctrx[jx], m_here, col)

    # Create the vertical lines
    if vlineson:
        c.line(ltm, mtop, ltm, mbot)
        for l in sdsx:
            c.line(l, mtop, l, mbot)


def addpayment(file1, cache, amtowed, payment, paidon, payref, paymethod):
    baldue = float(amtowed) - float(payment)
    try:
        paidon = paidon.strftime('%m/%d/%Y')
    except:
        print('Already a string')
    file2 = file1.replace('.pdf', f'_Paid{cache}.pdf')
    file2 = file2.replace('/vInvoice','/vPaidInvoice')
    c = canvas.Canvas(file2, pagesize=letter)
    c.setLineWidth(1)
    c.setFillColor('white')
    c.rect(395, 54.8, 180, 70.4, fill=True, stroke=True)
    c.setFillColor('black')
    m6 = 125.2
    bottomline = m6 - 15
    c.setFont('Times-Roman', 10, leading=None)
    c.drawString(400, bottomline, paidon)
    c.drawRightString(570, bottomline - 20, f'{paymethod} Reference #{payref}')

    c.setFont('Times-Bold', 10, leading=None)
    c.drawRightString(570, bottomline, f'Applied Payment: ${d2s(payment)}')
    c.drawRightString(570, bottomline-40, f'Balance Remaining: ${d2s(baldue)}')

    if baldue < .01:
        filepath = addpath(f'static/{scac}/data/stamps/paid.png')
        image = Image.open(filepath)
        stamp_right = 115
        stamp_up = 180
        c.drawImage(filepath, stamp_right, stamp_up, mask='auto')

    c.showPage()
    c.save()
    cache, docrefx = pagemerger([file2, file1], cache)
    os.rename(addpath(docrefx), file2)
    return os.path.basename(file2)


def make_invo_doc(odata, ldata, pdata1, cache, invodate, payment, tablesetup, invostyle):

# All dates must begin in datetime format and will be converted to strings as required

    joborder = odata.Jo
    file1 = addpath(f'static/{scac}/data/vInvoice/INV'+joborder+'.pdf')
    file2 = addpath(f'static/{scac}/data/vInvoice/INV'+joborder+'c'+str(cache)+'.pdf')
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
    header_font = 'Helvetica'
    header_fontsize = 11
    headerval_font = 'Helvetica'
    headerval_fontsize = 9

    ltm, ctrall, rtm = 36, 310, 575
    dl, hls = 17.6, 530
    m1, m2, m3, m4, m5, m6, m7 = hls - dl, hls - 2 * dl, hls - 3 * dl, hls - 4 * dl, hls - 18 * dl, hls - 23 * dl, hls - 27 * dl
    fulllinesat = [m1, m2, m3, m4, m5, m6, m7]
    dateline = m1+8.2*dl
    p1, p2, p3, p4, p5 = ltm + 87, ltm + 180, ctrall, rtm - 180, rtm - 100
    n1, n2, n3, n4 = ltm + 58, ltm + 128, rtm - 140, rtm - 70
    sds2 = [n1, n2, n3, n4]
    q1, q2 = ltm + 180, rtm - 180
    sds3 = [q1, q2]
    bump = 2.5
    tb = bump * 2
    dh = 12
    ct = 305
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

    # Date and JO boxes
    c.setFont('Helvetica', 11, leading=None)
    c.rect(rtm-150, m1+7*dl, 150, 2*dl, stroke=1, fill=0)
    c.line(rtm-150, dateline, rtm, dateline)
    c.line(rtm-75, m1+7*dl, rtm-75, m1+9*dl)
    c.drawCentredString(rtm-112.5, dateline+bump, 'Date')
    c.drawCentredString(rtm-37.7, dateline+bump, 'Invoice #')
    x = avg(rtm - 75, rtm)
    y = dateline - dh - bump
    c.setFont('Helvetica', 10, leading=None)
    c.drawCentredString(x, y, joborder)
    x = avg(rtm - 75, rtm - 150)
    c.drawCentredString(x, y, invodate)

    # Top Boxes (Address boxes)
    c.setFont('Helvetica', 11, leading=None)
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
        top = scroll_write(c,'Helvetica',10,level1-dh,ltm+bump*3,13,billto, 175-bump*5)

    if lh1 > 1:
        c.rect(ctm, m1 + dl, 175, 5 * dl, stroke=1, fill=0)
        c.line(ctm, level1, ctm + 175, level1)
        c.drawString(ctm + bump * 3, m1 + 5 * dl + bump * 2, f'{header1[1]}')
        pdata2 = odata.Dropblock1
        try:
            pdata2 = pdata2.splitlines()
        except:
            pdata2 = []
        loadat = []
        for dat in pdata2:
            loadat.append(dat)
        if loadat == []:
            for i in range(5):
                loadat.append('')
        top = scroll_write(c, 'Helvetica', 10, level1 - dh, ctm + bump * 3, 13, loadat, 175-bump*5)

    if lh1 > 2:
        c.rect(rtm - 175, m1 + dl, 175, 5 * dl, stroke=1, fill=0)
        c.line(rtm - 175, level1, rtm, level1)
        c.drawString(rtm - 170 + bump * 2, m1 + 5 * dl + bump * 2, f'{header1[2]}')
        pdata3 = odata.Dropblock2
        try:
            pdata3 = pdata3.splitlines()
        except:
            pdata3 = []
        shipto = []
        for dat in pdata3:
            shipto.append(dat)
        if shipto == []:
            for i in range(5):
                shipto.append('')
        top = scroll_write(c, 'Helvetica', 10, level1 - dh, rtm - 175 + bump * 3, 13, shipto, 175-bump*5)


    #Create the middle row headers and auto fit the width for the items
    header2 = tablesetup['invoicetypes'][invostyle]['Middle Blocks']
    header2items = tablesetup['invoicetypes'][invostyle]['Middle Items']
    thisctr, thislft, header2vals = center_write(odata, header2, header2items, 11, 9, ltm, rtm)
    c.setFont('Helvetica', 11, leading=None)
    for jx, header in enumerate(header2):
        c.drawCentredString(thisctr[jx], m2+tb, header)
    c.setFont('Helvetica', 9, leading=None)
    for jx, header in enumerate(header2vals):
        c.drawCentredString(thisctr[jx], m3+tb, nononestr(header))
    for lft in thislft:
        c.line(lft, m1, lft, m3)

    # Create the lower row headers
    c.setFont('Helvetica', 11, leading=None)
    header3 = tablesetup['invoicetypes'][invostyle]['Lower Blocks']
    ctr = [avg(ltm, n1), avg(n1, n2), avg(n2, n3), avg(n3, n4), avg(n4, rtm)]
    for jx, header in enumerate(header3):
        c.drawCentredString(ctr[jx], m4+tb, header)




    top = m6-1.5*dh
    for bline in bank:
        c.drawCentredString(ct, top, bline)
        top = top-dh

    top = m1+9*dl-5
    for usline in us:
        c.drawString(ltm+bump, top, usline)
        top = top-dh

    #c.setFillColor('white')
    #c.rect(395,54.8,180,70.4, fill=True, stroke=True)
    #c.setFillColor('black')

    bottomline = m6-23
    c.setFont('Helvetica-Bold', 12, leading=None)
    c.drawString(q2+tb, bottomline, 'Balance Due:')

    c.setFont('Helvetica', 10, leading=None)
    c.drawCentredString(avg(q2, rtm), m7+12, 'Add $39.00 for all international wires')

    c.setFont('Times-Roman', 9, leading=None)
    j = 0
    dh = 9.95
    top = m5-dh
    for noteline in note:
        c.drawString(ltm+tb, top, noteline)
        top = top-dh


# _______________________________________________________________________
    # Insert data here
# _______________________________________________________________________
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

        xdist, top = write_lines(c, n3-n2, line5, 'Helvetica', 9, n2 + tb, top, dh)

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

def make_summary_doc(sdata, sdat, pdat, cache, invodate, payment, tablesetup, invostyle):

# All dates must begin in datetime format and will be converted to strings as required

    si = sdat.Si
    docref = sdat.Source
    newbase = f'{si}_c{cache}.pdf'
    file1 = addpath(f'static/{scac}/data/vInvoice/{docref}')
    file2 = addpath(f'static/{scac}/data/vInvoice/{si}_c{cache}.pdf')
    today = datetime.datetime.today().strftime('%m/%d/%Y')

    if invodate is None or invodate == 0:
        invodate = today
    else:
        invodate = invodate.strftime('%m/%d/%Y')

    # Set numberical formatting values:
    header_font = 'Helvetica'
    header_fontsize = 11
    headerval_font = 'Helvetica'
    headerval_fontsize = 9

    ltm, ctrall, rtm = 36, 310, 575
    dl, hls = 17.6, 530
    m1, m2, m3, m4, m5, m6, m7 = hls - dl, hls - 2 * dl, hls - 3 * dl, hls - 4 * dl, hls - 18 * dl, hls - 23 * dl, hls - 27 * dl
    #Create the horizontal lines
    fulllinesat = [m1, m2, m5, m6, m7]
    dateline = m1+8.2*dl
    p1, p2, p3, p4, p5 = ltm + 87, ltm + 180, ctrall, rtm - 180, rtm - 100
    n1, n2, n3, n4 = ltm + 58, ltm + 128, rtm - 140, rtm - 70
    sds2 = [n1, n2, n3, n4]
    q1, q2 = ltm + 180, rtm - 180
    sds3 = [q1, q2]
    bump = 2.5
    tb = bump * 2
    dh = 12
    ct = 305
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


    for m in sds3:
        c.line(m, m6, m, m7)
    c.line(ltm, m1, ltm, m7)
    c.line(rtm, m1, rtm, m7)
    h1 = avg(m6, m7)-3
    c.line(q2, h1, rtm, h1)

    # Write the document title
    c.setFont('Helvetica-Bold', 24, leading=None)
    c.drawCentredString(rtm-75, dateline+1.5*dl, 'Invoice')

    # Date and JO boxes
    c.setFont('Helvetica', 11, leading=None)
    c.rect(rtm-150, m1+7*dl, 150, 2*dl, stroke=1, fill=0)
    c.line(rtm-150, dateline, rtm, dateline)
    c.line(rtm-75, m1+7*dl, rtm-75, m1+9*dl)
    c.drawCentredString(rtm-112.5, dateline+bump, 'Date')
    c.drawCentredString(rtm-37.7, dateline+bump, 'Invoice #')
    x = avg(rtm - 75, rtm)
    y = dateline - dh - bump
    c.setFont('Helvetica', 10, leading=None)
    c.drawCentredString(x, y, si)
    x = avg(rtm - 75, rtm - 150)
    c.drawCentredString(x, y, invodate)

    # Top Boxes (Address boxes)
    c.setFont('Helvetica', 11, leading=None)
    ctm = 218
    level1 = m1+5*dl
    header1 = tablesetup['summarytypes'][invostyle]['Top Blocks']
    lh1 = len(header1)

    if lh1 > 0:
        c.rect(ltm, m1 + dl, 175, 5 * dl, stroke=1, fill=0)
        c.line(ltm, level1, ltm + 175, level1)
        c.drawString(ltm + bump * 3, m1 + 5 * dl + bump * 2, f'{header1[0]}')
        billto = list(range(5))
        if pdat is not None:
            billto[0] = comporname(pdat.Company, fullname(pdat.First, pdat.Middle, pdat.Last))
            billto[1] = nononestr(pdat.Addr1)
            billto[2] = nononestr(pdat.Addr2)
            billto[3] = nononestr(pdat.Telephone)
            # billto[4]=nononestr(pdata1.Email)
            billto[4] = ' '
        else:
            for i in range(5):
                billto[i] = ' '
        top = scroll_write(c,'Helvetica',10,level1-dh,ltm+bump*3,13,billto, 175-bump*5)

    # Create the lower row headers
    all_lines = []
    total = 0

    for sidat in sdata:
        jo = sidat.Jo
        date1 = sidat.Begin.strftime('%m/%d/%Y')
        date2 = sidat.End.strftime('%m/%d/%Y')
        amount = sidat.Amount
        gate = f'{date1}-{date2}'
        con = f'{sidat.Container} {sidat.Type}'
        try:
            total = total + float(amount)
        except:
            amount = 0.00
        line7 = [jo, gate, sidat.Release, con, sidat.Description, str(amount)]
        all_lines.append(line7)

    c.setFont('Helvetica', 11, leading=None)
    header3 = tablesetup['summarytypes'][invostyle]['Lower Blocks']
    hlen = len(header3)
    max_block = 4
    spread = 8
    min_w = []
    for header in header3:
        thisw = stringWidth(header, 'Helvetica', 11)
        #print(f'header {header} {thisw}')
        thisw = thisw + spread
        min_w.append(thisw)
    for line in all_lines:
        for kx, element in enumerate(line):
            thisw = stringWidth(element, 'Times-Roman', 9) + 5
            thatw = min_w[kx]
            new_min = max(thisw,thatw)
            min_w[kx] = new_min
    min_w[max_block] = 0
    total_spread = sum(min_w)
    width_avail = rtm-ltm
    mx_len = width_avail - total_spread
    min_w[max_block] = mx_len
    #print(f'Here are the widths: {min_w}')
    ctrx = []
    sdsx = []
    thisctr = ltm
    thisend = ltm
    for ix, header in enumerate(header3):
        if ix < hlen:
            thisctr = thisend + min_w[ix]/2
            thisend = thisend + min_w[ix]
        ctrx.append(thisctr)
        sdsx.append(thisend)

    for jx, header in enumerate(header3):
        c.drawCentredString(ctrx[jx], m2+tb, header)

    #Create the vertical lines
    for l in sdsx:
        c.line(l, m2, l, m5)

    top = m6-1.5*dh
    for bline in bank:
        c.drawCentredString(ct, top, bline)
        top = top-dh

    top = m1+9*dl-5
    for usline in us:
        c.drawString(ltm+bump, top, usline)
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
    for noteline in note:
        c.drawString(ltm+tb, top, noteline)
        top = top-dh


# _______________________________________________________________________
    # Insert data here
# _______________________________________________________________________
    top = m2-dh*2

    for line7 in all_lines:
        popdown = top
        for ix, strx in enumerate(line7):
            if ix == max_block:
                lines = simpleSplit(strx, 'Times-Roman', 9, mx_len)
                for line in lines:
                    c.drawString(sdsx[ix-1]+5, popdown, line)
                    popdown = popdown - 1.1*dh
            else:
                c.drawCentredString(ctrx[ix], top, strx)

        top = popdown - .4*dh

        #xdist, top = write_lines(c, n3-n2, line5, 'Helvetica', 9, n2 + tb, top, dh)

        #top = top-1.5*dh

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
    c.setFont('Helvetica-Bold', 12, leading=None)
    c.drawRightString(rtm-tb*2, bottomline, dollar(total))

    c.showPage()
    c.save()
    #
    # Now make a cache copy
    shutil.copy(file1, file2)

    return file2, newbase

def getzip(addr):
    try:
        items = addr.split()
        zip = items[-1]
        if len(zip)==5 or len(zip)==10:
            return zip
        else:
            return 0
    except:
        return 0


def writechecks(sids,pmeth):
    #Functions for turning numbers into words imported from class8_utils.py

    sid = sids[0]
    rows = len(sids) + 1
    bdat = Bills.query.get(sid)
    pdat = People.query.get(bdat.Pid)
    if len(sids) > 1: multi = True
    else: multi = False


    ckstyle = request.values.get('ckstyle')
    if ckstyle is None: ckstyle = 1
    else: ckstyle = int(ckstyle)

    billno = bdat.Jo

    try: cache = int(bdat.Ccache)
    except: cache = 0

    if pmeth == 'Check':
        if multi: docref = f'Check_{billno}_Multi_c{cache}.pdf'
        else: docref = f'Check_{billno}_c{cache}.pdf'
    else:
        if multi: docref = f'Payment_{billno}_Multi_c{cache}.pdf'
        else: docref = f'Payment_{billno}_c{cache}.pdf'

    file1 = addpath(f'static/{scac}/data/vCheck/{docref}')
    bdat.Ccache = cache + 1
    db.session.commit()
    print(f'The check docref is {docref} and ckstyle is {ckstyle}')

    try:
        if multi: amt = bdat.pAmount2
        else: amt = bdat.pAmount
        amt = amt.replace(',', '')
        amount = float(amt)
    except:
        amt = bdat.bAmount
        amount = float(amt)

    # Create the Check Date:
    billdate = bdat.pDate
    try: datestr = billdate.strftime('%m/%d/%Y')
    except: datestr = datetime.datetime.today().strftime('%m/%d/%Y')

    if bdat.Memo is None: memo = ' '
    else: memo = bdat.Memo

    if bdat.Description is None: desc = ' '
    else: desc = bdat.Description
    payref = bdat.Ref

    # Check to see if we have the required data to make an invoice:
    payee = pdat.Company
    addr1 = pdat.Addr1
    addr2 = pdat.Addr2

    amount_num = d2s(amount)
    bank = bdat.pAccount
    amount_text = get_check_words(amount_num)
    # print(amount_text)

    # We need to add '*******' to back of this enough to fill up the rest of the block
    atlen = len(amount_text)
    addstar = '*' * (90-atlen)
    amount_text = f'{amount_text}{addstar}'

    c = canvas.Canvas(file1,  pagesize=letter)
    c.setFont('Helvetica', 12, leading=None)

# Main check writing (top 1/3)
    if pmeth == 'Check':
        c.drawString(515, 720, datestr)
        c.drawString(70, 685, payee)
        c.drawString(500, 686, amount_num)
        c.drawString(30, 660, amount_text)
        c.drawString(52, 592, memo)

    ltm, ctrall, rtm = 15, 310, 590
    dl, hls = 17.6, 530

    m1 = 510
    m2 = m1-dl
    m3 = m2-dl
    m4 = m3-10
    m5 = m4-dl
    m6 = m5-dl
    m7 = 265
    m8 = m7-dl
    m9 = m8-dl
    m10 = m9-10
    m11 = m10-dl
    m12 = m11-dl

    n1 = ltm+90
    n2 = n1+150
    n3 = n2+80
    n4 = n3+80
    n5 = rtm-90

    btype = bdat.bType
    bcat = bdat.bCat
    bsubcat = bdat.bSubcat
    acct = bdat.bAccount
    comp = bdat.Co
    if acct is None: acct = ' '
    if comp is None: comp = ' '
    bacct = f'{acct} ({comp})'
    if multi:
        #We need to know if we can label the top with same info or if it varies and thus cannot
        joset, pamtset, btypset, bcatset, bsubcatset, bacctset, paidset = [], [], [], [], [], [], []
        for sid in sids:
            cdat = Bills.query.get(sid)
            joset.append(cdat.Jo)
            pamtset.append(cdat.pAmount)
            btypset.append(cdat.bType)
            bcatset.append(cdat.bCat)
            bsubcatset.append(cdat.bSubcat)
            bacctset.append(cdat.bAccount)
            paidset.append(cdat.Status)

        if sameall(joset): billno = joset[0]
        else: billno = 'Multiple'
        if sameall(btypset): btype = btypset[0]
        else: btype = 'Multiple'
        if sameall(bcatset): bcat = bcatset[0]
        else: bcat = 'Multiple'
        if sameall(bsubcatset): bsubcat = bsubcatset[0]
        else: bsubcat = 'Multiple'
        if sameall(bacctset): bacct = bacctset[0]
        else: bacct = 'Multiple'
    else:
        cdat = Bills.query.get(sid)
        paidset = [cdat.Status]

    item11 = ['Date', 'Ck No.', 'Type', 'Category', 'Subcategory', 'Account']
    item12 = [datestr, payref, btype, bcat, bsubcat, bacct]
    item21 = ['BillNo', 'Amount', 'Check Made Out To', 'From Acct']
    item22 = [billno, amount_num, payee, bank]
    if multi:
        itemheads = ['BillRef', 'Amount', 'Type', 'Category', 'Subcategory', 'Account']
        itemeachs = []
        for ix, sid in enumerate(sids):
            itemeachs.append([joset[ix], pamtset[ix], btypset[ix], bcatset[ix], bsubcatset[ix], bacctset[ix]])


    if pmeth == 'Check':
        #Only sign check if all items are paid and recorded
        if sameall(paidset) and paidset[0] == 'Paid':
            image = addpath(f'static/{scac}/pics/ck_sigfile.png')
            c.drawImage(image, 374, 587, width=200, height=40)
        else:
            c.setFont('Helvetica-Bold', 14, leading=None)
            c.drawString(374, 587, '***Void Until Recorded***')
            c.setFont('Helvetica', 12, leading=None)

# Middle 1/3 section ********** only print this section if making a payment record that is not a check

        memoline2 = m6 - dl * 2
        if ckstyle == 1:
            font = 'Helvetica'
            fontsize = 12
            opto_table(c, item11, [item12], font, fontsize, ltm, rtm, m1, m3, 5, True, True, True)
            opto_table(c, item21, [item22], font, fontsize, ltm, rtm, m4, m6, 2, True, True, True)

            if multi:
                mtop = m6 - dl
                if rows > 6 :
                    dr = dl*7/rows
                    fontsize = 11
                    if rows > 12: fontsize = 10
                else:
                    dr = dl
                    fontsize = 12
                opto_table(c, itemheads, itemeachs, font, fontsize, ltm, rtm, mtop, mtop - dr*rows, 5, True, False, False)

            else:
                mtop = m6 - dl * 2
                c.drawString(ltm + 20, mtop, f'Memo on Check:  {memo}')
                mtop = mtop - dl
                c.drawString(ltm + 20, mtop, f'Full Description:  {desc}')
                mtop = mtop - dl*2

                c.drawString(ltm + 20, mtop, 'Paid To (Name and Address):')
                mtop = mtop - dl
                c.drawString(ltm + 20, mtop, payee)
                mtop = mtop - dl
                c.drawString(ltm + 20, mtop, addr1)
                mtop = mtop - dl
                c.drawString(ltm + 20, mtop, addr2)


        else:
            cdata = companydata()
            c.setFont('Helvetica', 12, leading=None)
            offup = 5
            c.drawString(50, m2+offup, cdata[2])
            c.drawString(50, m2+offup-14, cdata[5])
            c.drawString(50, m2+offup-28, cdata[6])
            memoline2 = memoline2 + 1
            c.drawString(ltm+70, memoline2, payee)
            c.drawString(ltm+70, memoline2-14, addr1)
            c.drawString(ltm+70, memoline2-28, addr2)
            zip = getzip(addr2)
            #print('myzipcode is',zip)
            if zip != 0:
                barcode_usps = usps.POSTNET(zip)
                barcode_usps.drawOn(c,ltm+70,memoline2-42)

    #Bottom 1/3rd labels

        font = 'Helvetica'
        fontsize = 12
        opto_table(c, item11, [item12], font, fontsize, ltm, rtm, m7, m9, 5, True, True, True)
        opto_table(c, item21, [item22], font, fontsize, ltm, rtm, m10, m12, 2, True, True, True)

        if multi:
            mtop = m12 - dl
            if rows > 6:
                dr = dl * 7 / rows
                fontsize = 11
                if rows > 12: fontsize = 10
            else:
                dr = dl
                fontsize = 12
            opto_table(c, itemheads, itemeachs, font, fontsize, ltm, rtm, mtop, mtop - dr * rows, 5, True, False, False)

        else:
            mtop = m12 - dl * 2
            c.drawString(ltm + 20, mtop, f'Memo on Check:  {memo}')
            mtop = mtop - dl
            c.drawString(ltm + 20, mtop, f'Full Description:  {desc}')
            mtop = mtop - dl * 2

            c.drawString(ltm + 20, mtop, 'Paid To (Name and Address):')
            mtop = mtop - dl
            c.drawString(ltm + 20, mtop, payee)
            mtop = mtop - dl
            c.drawString(ltm + 20, mtop, addr1)
            mtop = mtop - dl
            c.drawString(ltm + 20, mtop, addr2)

    else:
        # Payment record if not writing a check
        c.drawCentredString(ltm+(rtm-ltm)/2,750,f'{pmeth} Payment Record')
        if sameall(paidset) and paidset[0] == 'Paid':
            c.drawCentredString(ltm + (rtm - ltm) / 2, 735, 'Payment has been Recorded in Register')
        else:
            c.drawCentredString(ltm + (rtm - ltm) / 2, 735, '***Void Until Recorded***')
        m1 = 720
        m2 = m1 - dl
        m3 = m2 - dl
        m4 = m3 - 10
        m5 = m4 - dl
        m6 = m5 - dl
        font = 'Helvetica'
        fontsize = 12
        opto_table(c, item11, [item12], font, fontsize, ltm, rtm, m1, m3, 5, True, True, True)
        opto_table(c, item21, [item22], font, fontsize, ltm, rtm, m4, m6, 2, True, True, True)

        if multi:
            mtop = m6 - dl
            if rows > 6:
                dr = dl * 7 / rows
                fontsize = 11
                if rows > 12: fontsize = 10
            else:
                dr = dl
                fontsize = 12
            opto_table(c, itemheads, itemeachs, font, fontsize, ltm, rtm, mtop, mtop - dr * rows, 5, True, False, False)

        else:
            mtop = m6 - dl * 2
            c.drawString(ltm + 20, mtop, f'Memo:  {memo}')
            mtop = mtop - dl
            c.drawString(ltm + 20, mtop, f'Full Description:  {desc}')
            mtop = mtop - dl * 2

            c.drawString(ltm + 20, mtop, 'Paid To:')
            mtop = mtop - dl
            c.drawString(ltm + 20, mtop, payee)
            mtop = mtop - dl
            c.drawString(ltm + 20, mtop, addr1)
            mtop = mtop - dl
            c.drawString(ltm + 20, mtop, addr2)


    c.showPage()
    c.save()
    return docref, file1, cache, ckstyle