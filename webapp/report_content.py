from flask import session, logging, request

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.pagesizes import landscape
from reportlab.platypus import Image
from reportlab.lib.units import inch
from webapp.viewfuncs import nonone, nononef, nononestr, dollar, avg, comporname, fullname, address, d2s, newjo
import csv
import math
import datetime
from webapp import db
from webapp.models import JO, OverSeas, Orders, People, Invoices, Income, Interchange, Bills, Accounts
import subprocess
from webapp.CCC_system_setup import myoslist,addpath,addtxt, scac

#This function defines all the report parameters normally used
def reportsettings(squeeze):
    #squeeze input is squeeze factor to apply to default spacing parameters squeeze=1 is default call
    #Left and right margins:
    ltm=36
    rtm=575
    # Offsets from lines:
    bump=2.5
    tb=bump*2
    #Center Points
    ctrall=310
    left_ctr=170
    right_ctr=480

    dl=17.6
    tdl=dl*2
    dh=dl*.9*squeeze
    hls=530
    m1=hls-dl
    m2=hls-2*dl
    m3=hls-3*dl
    m4=hls-4*dl
    m5=hls-18*dl
    m6=hls-23*dl
    m7=hls-27*dl
    n1=550
    n2=n1-dl
    n3=hls-27*dl

    return ltm,rtm,bump,tb,ctrall,left_ctr,right_ctr,dl,dh,tdl,hls,m1,m2,m3,m4,m5,m6,m7,n1,n2,n3

def depositcontents(file4,itemlist,cache,nextjo,acctin,stamp):

    today = datetime.datetime.today().strftime('%m/%d/%Y')
    invodate = datetime.date.today().strftime('%m/%d/%Y')
    adat = Accounts.query.filter(Accounts.Name==acctin).first()
    if adat is not None:
        rt = adat.Routing
        an = adat.AcctNumber
    else:
        rt = 'Unknown'
        an = 'Unknow'


    ltm,rtm,bump,tb,ctrall,left_ctr,right_ctr,dl,dh,tdl,hls,m1,m2,m3,m4,m5,m6,m7,n1,n2,n3=reportsettings(1)

    pages=[file4]
    page=1
    c=canvas.Canvas(file4, pagesize=letter)
    c.setLineWidth(1)

    place=[ltm+10,ltm+90,ltm+270,ltm+450,ltm+500,rtm-80]
    ctr=[]
    for j,p in enumerate(place):
        if j<len(place)-1:
            ctr.append(avg(p,place[j+1]))

    #Main Items Listing
    c.setFont('Helvetica-Bold',14,leading=None)
    c.drawString(45,550,'Deposit Ticket '+nextjo)
    c.drawString(45,530,'Bank Account: '+acctin)
    c.drawString(305, 550, 'Account Number: ' + an)
    c.drawString(305, 530, 'Bank Routing: ' + rt)


    c.setFont('Helvetica-Bold',12,leading=None)

    top = n2+dh-50
    c.drawString(place[0],top,'Checks Deposited: Details by Job Order')

    top = top - dl
    for j,i in enumerate(['Job Order','Customer','Remit/Check Ref #','Amount']):
        if j==3:
            c.drawRightString(place[j],top,i)
        else:
            c.drawString(place[j],top,i)

    c.setFont('Helvetica',12,leading=None)
    top = top - dh
    total = 0.00
    checks = []
    cktotals = []
    complist = []
    l1=len(itemlist)
    for k in range(l1):
        newlist=itemlist[k]
        for j,i in enumerate(newlist):

            if j==2:
                if i not in checks:
                    checks.append(i)
                    complist.append(newlist[1])

            if j == 3:
                c.drawRightString(place[j],top,i)
                amt = float(i)
                total = total + amt
            else:
                c.drawString(place[j],top,i)
        top=top-dl

        if top<n3:
            c.showPage()
            c.save()
            page=page+1
            base=file4.replace('.pdf','')
            newfile=base+'page'+str(page)+'.pdf'
            top = n2-dh
            c=canvas.Canvas(newfile, pagesize=letter)
            pages.append(newfile)

    totals =d2s(total)
    c.setFont('Helvetica-Bold',12,leading=None)
    c.drawString(place[2],top,'Total:')
    c.drawRightString(place[3],top,totals)

    for ch in checks:
        subtotal = 0.00
        for items in itemlist:
            if items[2]==ch:
                amt = float(items[3])
                subtotal = subtotal + amt
        cktotals.append(subtotal)

    #Main Items Listing
    c.setFont('Helvetica-Bold',12,leading=None)

    top = top - 2*dh
    c.drawString(place[0],top,'Checks Deposited: Summary by Check')
    top = top-dl
    for j,i in enumerate(['Check#','Customer','','Amount']):
        if j==3:
            c.drawRightString(place[j],top,i)
        else:
            c.drawString(place[j],top,i)

    c.setFont('Helvetica',12,leading=None)
    top = top - dh
    total = 0.00
    for j,ch in enumerate(checks):
        c.drawString(place[0],top,ch)
        c.drawString(place[1],top,complist[j])
        c.drawRightString(place[3],top,d2s(cktotals[j]))
        top = top - dh

    c.setFont('Helvetica-Bold',12,leading=None)
    c.drawString(place[2],top,'Total:')
    c.drawRightString(place[3],top,totals)

    if stamp==1:
        c.setFont('Helvetica-Bold',14,leading=None)
        top=top-3*dh
        depstamp = addpath(f"tmp/{scac}/pics/deposited.png")
        c.drawImage(depstamp, 135, 50, mask='auto')
        c.drawCentredString(307,65,today)
        jdat=JO.query.filter(JO.jo==nextjo).first()
        jdat.dinc=d2s(totals)
        db.session.commit()

    c.showPage()
    c.save()

    if len(pages)>1:
        pdfcommand=['pdfunite']
        for page in pages:
            pdfcommand.append(page)
        multioutput=addpath(f'tmp/{scac}/data/vreport/multioutput'+str(cache)+'.pdf')
        pdfcommand.append(multioutput)
        tes=subprocess.check_output(pdfcommand)
    else:
        multioutput=''

    return pages,multioutput

def incomecontents(file4,itemlist,cache):

    today = datetime.datetime.today().strftime('%m/%d/%Y')
    invodate = datetime.date.today().strftime('%m/%d/%Y')
    sdate=request.values.get('start')
    fdate=request.values.get('finish')
    try:
        start=datetime.datetime.strptime(sdate, '%Y-%m-%d')
        end=datetime.datetime.strptime(fdate, '%Y-%m-%d')
    except:
        start=today
        end=today

    ltm,rtm,bump,tb,ctrall,left_ctr,right_ctr,dl,dh,tdl,hls,m1,m2,m3,m4,m5,m6,m7,n1,n2,n3=reportsettings(1)

    pages=[file4]
    page=1
    c=canvas.Canvas(file4, pagesize=letter)
    c.setLineWidth(1)

    place=[ltm+10,ltm+80,ltm+140,ltm+280,ltm+410,rtm-80]
    ctr=[]
    for j,p in enumerate(place):
        if j<len(place)-1:
            ctr.append(avg(p,place[j+1]))

    #Main Items Listing
    c.setFont('Helvetica',12,leading=None)

    l1=len(itemlist)
    top = n2-dh
    for k in range(l1):
        newlist=itemlist[k]
        for j,i in enumerate(newlist):
            if j==5:
                c.drawRightString(rtm-10,top,i)
            else:
                c.drawString(place[j],top,i)
        top=top-dl
        if top<n3:
            c.showPage()
            c.save()
            page=page+1
            base=file4.replace('.pdf','')
            newfile=base+'page'+str(page)+'.pdf'
            top = n2-dh
            c=canvas.Canvas(newfile, pagesize=letter)
            pages.append(newfile)

    c.showPage()
    c.save()

    if len(pages)>1:
        pdfcommand=['pdfunite']
        for page in pages:
            pdfcommand.append(page)
        multioutput=addpath(f'tmp/{scac}/data/vreport/multioutput'+str(cache)+'.pdf')
        pdfcommand.append(multioutput)
        tes=subprocess.check_output(pdfcommand)
    else:
        multioutput=''

    return pages,multioutput




def ticketcontents(file4,itemlist):

    today = datetime.datetime.today().strftime('%m/%d/%Y')
    invodate = datetime.date.today().strftime('%m/%d/%Y')
    sdate=request.values.get('start')
    fdate=request.values.get('finish')
    try:
        start=datetime.datetime.strptime(sdate, '%Y-%m-%d')
        end=datetime.datetime.strptime(fdate, '%Y-%m-%d')
    except:
        start=today
        end=today

    ltm,rtm,bump,tb,ctrall,left_ctr,right_ctr,dl,dh,tdl,hls,m1,m2,m3,m4,m5,m6,m7,n1,n2,n3=reportsettings(1)

    c=canvas.Canvas(file4, pagesize=letter)
    c.setLineWidth(1)

    place=[ltm+10,ltm+100,ltm+180,ltm+280,ltm+370,rtm-100]
    ctr=[]
    for j,p in enumerate(place):
        if j<len(place)-1:
            ctr.append(avg(p,place[j+1]))

    #Main Items Listing
    c.setFont('Helvetica',12,leading=None)
    l1=len(itemlist)
    top = n2-dh
    for k in range(l1):
        newlist=itemlist[k]
        for j,i in enumerate(newlist):
            c.drawString(place[j],top,i)
        top=top-dl

    c.showPage()
    c.save()
#_____________________________________________________________________________
#_____________________________________________________________________________
#_____________________________________________________________________________
def stripheader(c,fsize,mtop,hvec,items):
    c.setFont('Helvetica-Bold',fsize,leading=None)
    litem=len(items)
    lm=hvec[0]
    rm=hvec[litem]
    sds1=hvec[1:litem]
    n2=mtop-1.4*fsize
    for k in sds1:
        c.line(k,mtop,k,n2)

    c.line(lm,mtop,rm,mtop)
    mtop=mtop-1.4*fsize
    c.line(lm,mtop,rm,mtop)
    mstr=mtop+.2*fsize+1
    ctr=[]
    for j,hpt in enumerate(hvec):
        if j<litem:
            ctr.append(avg(hpt,hvec[j+1]))
    for j,i in enumerate(items):
        c.drawCentredString(ctr[j],mstr,i)
    return mtop


def itemlisting(c,fsize,mtop,hvec,itemslist,total,bottomy):
    c.setFont('Helvetica-Bold',fsize,leading=None)
    l1=len(itemslist)
    dl=fsize*2
    dh=dl*.6
    bump=2.5
    mtop = mtop-dh
    ctr=[]
    for j,hpt in enumerate(hvec):
        if j<len(hvec)-1:
            ctr.append(avg(hpt,hvec[j+1]))

    if l1==0:
        print('hvec=',hvec)
        c.drawString(hvec[4],mtop,'No Items Reported This Period')
        mtop=mtop-dh

    for k in range(l1):
        newlist=itemslist[k]
        for j,i in enumerate(newlist):
            if j==8:
                c.drawRightString(hvec[j+1]-bump,mtop,i)
            elif j==7:
                c.drawRightString(hvec[j+1],mtop,i)
            elif j==5:
                c.drawRightString(hvec[j+1],mtop,i)
            elif j==4:
                if len(i)>30:
                    i=i[0:30]
                c.drawString(hvec[j],mtop,i)
            else:
                try:
                    c.drawCentredString(ctr[j],mtop,i)
                except:
                    c.drawCentredString(ctr[j],mtop,'53 Dry Van')
        mtop=mtop-dh
        amount=newlist[8]
        total=total+float(amount)

        if mtop<bottomy+dh and k+1<l1:
            mtop=0
            rlist=itemslist[k+1:l1]
            return mtop,total,rlist

    return mtop,total,0

def paymentlisting(c,fsize,mtop,hvec,itemslist,total,bottomy):
    c.setFont('Helvetica-Bold',fsize,leading=None)
    l1=len(itemslist)
    dl=fsize*2
    dh=dl*.6
    bump=2.5
    mtop = mtop-dh
    ctr=[]
    for j,hpt in enumerate(hvec):
        if j<len(hvec)-1:
            ctr.append(avg(hpt,hvec[j+1]))

    if l1==0:
        c.drawString(hvec[4],mtop,'No Items Reported This Period')
        mtop=mtop-dh

    for k in range(l1):
        newlist=itemslist[k]
        for j,i in enumerate(newlist):
            if j==5:
                c.drawRightString(hvec[j+1]-bump,mtop,i)
            elif j==4:
                if len(i)>50:
                    i=i[0:50]
                c.drawString(hvec[j],mtop,i)
            else:
                try:
                    c.drawCentredString(ctr[j],mtop,i)
                except:
                    c.drawCentredString(ctr[j],mtop,'53 Dry Van')
        mtop=mtop-dh
        amount=newlist[5]
        total=total+float(amount)

        if mtop<bottomy+dh and k+1<l1:
            mtop=0
            rlist=itemslist[k+1:l1]
            return mtop,total,rlist

    return mtop,total,0

def billitemlisting(c,fsize,mtop,hvec,itemslist,total,bottomy):
    c.setFont('Helvetica-Bold',fsize,leading=None)
    l1=len(itemslist)
    dl=fsize*2
    dh=dl*.6
    bump=2.5
    mtop = mtop-dh
    ctr=[]
    for j,hpt in enumerate(hvec):
        if j<len(hvec)-1:
            ctr.append(avg(hpt,hvec[j+1]))

    if l1==0:
        print('hvec=',hvec)
        c.drawString(hvec[1],mtop,'No Items Reported This Period')
        mtop=mtop-dh

    for k in range(l1):
        newlist=itemslist[k]
        for j,i in enumerate(newlist):
            if j==2:
                c.drawRightString(hvec[j+1]-bump,mtop,i)
            elif j==1:
                if len(i)>50:
                    i=i[0:50]
                c.drawString(hvec[j],mtop,i)
            else:
                try:
                    c.drawCentredString(ctr[j],mtop,i)
                except:
                    c.drawCentredString(ctr[j],mtop,'53 Dry Van')
        mtop=mtop-dh
        amount=newlist[2]
        total=total+float(amount)

        if mtop<bottomy+dh and k+1<l1:
            mtop=0
            rlist=itemslist[k+1:l1]
            return mtop,total,rlist

    return mtop,total,0

def newpagecheck(c,mtop,bottomy,page,file4,pages):
    if mtop==0 or mtop<bottomy:
        c.showPage()
        c.save()
        page=page+1
        base=file4.replace('.pdf','')
        newfile=base+'page'+str(page)+'.pdf'
        c=canvas.Canvas(newfile, pagesize=letter)
        pages.append(newfile)
        mtop=580

    return c,page,pages,mtop





def jaycontents(file4,paiditems,servicelist,itemlist,bitemlist,total,btotal,nettotal,cache):


    ltm,rtm,bump,tb,ctrall,left_ctr,right_ctr,dl,dh,tdl,hls,m1,m2,m3,m4,m5,m6,m7,n1,n2,n3=reportsettings(1)
    pages=[file4]
    page=1
    c=canvas.Canvas(file4, pagesize=letter)
    c.setLineWidth(1)
    bottomy=n3
    badd=30


    p1=ltm+50
    p2=p1+50
    p3=p2+80
    p4=p3+70
    p5=rtm-132
    p7=rtm-100
    p8=rtm-70
    p9=rtm-40

    total=0.00

    hvec=[ltm,rtm]
    headerlist=['Credits']
    mtop=stripheader(c,12,n1,hvec,headerlist)

    hvec=[ltm,rtm]
    headerlist=['Payments Made']
    mtop=stripheader(c,11,mtop,hvec,headerlist)

    hvec=[ltm,p1,p2,p3,p4,p8,rtm]
    headerlist=['Start', 'Finish', 'Booking','Container','Summary','Paid Amount']
    mtop=stripheader(c,10,mtop,hvec,headerlist)

    mtop,total,rlist=paymentlisting(c,9,mtop,hvec,paiditems,total,bottomy)

    hvec=[ltm,rtm]
    headerlist=['Work Performed']
    mtop=stripheader(c,11,mtop,hvec,headerlist)

    hvec=[ltm,p1,p2,p3,p4,p5,p7,p8,p9,rtm]
    headerlist=['Start', 'Finish', 'Booking','Container','Summary','Gross','Days','Fees','NetP']
    mtop=stripheader(c,10,mtop,hvec,headerlist)

    mtop,total,rlist=itemlisting(c,9,mtop,hvec,itemlist,total,bottomy)
    #See if we bottomed out on page:
    if mtop==0:
        c.showPage()
        c.save()
        page=page+1
        base=file4.replace('.pdf','')
        newfile=base+'page'+str(page)+'.pdf'
        c=canvas.Canvas(newfile, pagesize=letter)
        pages.append(newfile)

        hvec=[ltm,rtm]
        headerlist=['Credits (continued)']
        mtop=stripheader(c,12,n1,hvec,headerlist)
        hvec=[ltm,rtm]
        headerlist=['Work Performed (continued)']
        mtop=stripheader(c,11,mtop,hvec,headerlist)

        hvec=[ltm,p1,p2,p3,p4,p5,p7,p8,p9,rtm]
        headerlist=['Start', 'Finish', 'Booking','Container','Summary','Gross','Days','Fees','NetP']
        mtop=stripheader(c,10,mtop,hvec,headerlist)

        mtop,total,rlist=itemlisting(c,9,mtop,hvec,rlist,total,bottomy)

    mtop=mtop-dh*1.2
    c.setFont('Helvetica-Bold',12,leading=None)
    c.drawRightString(p8,mtop+bump,'Credits Total:')
    c.drawRightString(rtm-bump,mtop+bump,dollar(total))

    credit_total=total

    mtop=mtop-dh
    c.line(ltm,mtop,rtm,mtop)
    mtop=mtop-.2*dh
    c.line(ltm,mtop,rtm,mtop)

    debit_total=0.0

    hvec=[ltm,rtm]
    headerlist=['Debits']
    mtop=stripheader(c,12,mtop,hvec,headerlist)

    c,page,pages,mtop=newpagecheck(c,mtop,bottomy+badd,page,file4,pages)

    hvec=[ltm,rtm]
    headerlist=['Services Used']
    mtop=stripheader(c,11,mtop,hvec,headerlist)

    c,page,pages,mtop=newpagecheck(c,mtop,bottomy+badd,page,file4,pages)

    hvec=[ltm,p1,p2,p3,p4,p8,rtm]
    headerlist=['Start', 'Finish', 'Booking','Container','Summary','Amount Due']
    mtop=stripheader(c,10,mtop,hvec,headerlist)

    mtop,debit_total,rlist=paymentlisting(c,9,mtop,hvec,paiditems,debit_total,bottomy)

    #See if we bottomed out on page:
    if mtop==0:
        c.showPage()
        c.save()
        page=page+1
        base=file4.replace('.pdf','')
        newfile=base+'page'+str(page)+'.pdf'
        c=canvas.Canvas(newfile, pagesize=letter)
        pages.append(newfile)

        hvec=[ltm,rtm]
        headerlist=['Debits (continued)']
        mtop=stripheader(c,12,n1,hvec,headerlist)
        hvec=[ltm,rtm]
        headerlist=['Services Used (continued)']
        mtop=stripheader(c,11,mtop,hvec,headerlist)

        hvec=[ltm,p1,p2,p3,p4,p8,rtm]
        headerlist=['Start', 'Finish', 'Booking','Container','Summary','Amount Due']
        mtop=stripheader(c,10,mtop,hvec,headerlist)

        mtop,debit_total,rlist=paymentlisting(c,9,mtop,hvec,rlist,debit_total,bottomy)

    c,page,pages,mtop=newpagecheck(c,mtop,bottomy+badd,page,file4,pages)

    hvec=[ltm,rtm]
    headerlist=['Bills to Jays Auto Account']
    mtop=stripheader(c,11,mtop,hvec,headerlist)

    c,page,pages,mtop=newpagecheck(c,mtop,bottomy+badd,page,file4,pages)

    hvec=[ltm,p3,p7,rtm]
    headerlist=['Date','Bill Summary', 'Amount']
    mtop=stripheader(c,10,mtop,hvec,headerlist)

    c,page,pages,mtop=newpagecheck(c,mtop,bottomy+badd,page,file4,pages)

    mtop,debit_total,rlist=billitemlisting(c,9,mtop,hvec,bitemlist,debit_total,bottomy)

    #See if we bottomed out on page:
    if mtop==0:
        c.showPage()
        c.save()
        page=page+1
        base=file4.replace('.pdf','')
        newfile=base+'page'+str(page)+'.pdf'
        c=canvas.Canvas(newfile, pagesize=letter)
        pages.append(newfile)

        hvec=[ltm,rtm]
        headerlist=['Debits (continued)']
        mtop=stripheader(c,12,n1,hvec,headerlist)
        hvec=[ltm,rtm]
        headerlist=['Bills to Jays Auto Account (continued)']
        mtop=stripheader(c,11,mtop,hvec,headerlist)

        hvec=[ltm,p3,p7,rtm]
        headerlist=['Date','Bill Summary', 'Amount']
        mtop=stripheader(c,10,mtop,hvec,headerlist)

        mtop,debit_total,rlist=billitemlisting(c,9,mtop,hvec,rlist,debit_total,bottomy)

    mtop=mtop-dh*1.2
    c.setFont('Helvetica-Bold',12,leading=None)
    c.drawRightString(p8,mtop+bump,'Debits Total:')
    c.drawRightString(rtm-bump,mtop+bump,dollar(debit_total))

    net=credit_total-debit_total

    bottomline=n3+bump
    c.setFont('Helvetica-Bold',12,leading=None)
    c.drawRightString(300,bottomline,'Balance Due:')
    c.drawString(300+bump,bottomline,dollar(net))

    c.showPage()
    c.save()

    if len(pages)>1:
        pdfcommand=['pdfunite']
        for page in pages:
            pdfcommand.append(page)
        multioutput=addpath(f'tmp/{scac}/data/vreport/multioutput'+str(cache)+'.pdf')
        pdfcommand.append(multioutput)
        tes=subprocess.check_output(pdfcommand)
    else:
        multioutput=''

    return pages,multioutput

def orderlisting(c,fsize,mtop,hvec,itemslist,justify,totals,bottomy):
    c.setFont('Helvetica-Bold',fsize,leading=None)
    l1=len(itemslist)
    dl=fsize*2
    dh=dl*.6
    bump=2.5
    sb=2
    mtop = mtop-dh
    ctr=[]
    for j,hpt in enumerate(hvec):
        if j<len(hvec)-1:
            ctr.append(avg(hpt,hvec[j+1]))

    if l1==0:
        c.drawString(hvec[4],mtop,'No Items Reported This Period')
        mtop=mtop-dh

    for k in range(l1):
        newlist=itemslist[k]
        for j,i in enumerate(newlist):
            if i is None: i = ''
            if justify[j]=='l':
                c.drawString(hvec[j]+sb,mtop,i)
            elif justify[j]=='c':
                c.drawCentredString(ctr[j],mtop,i)
            else:
                c.drawRightString(hvec[j+1]-sb,mtop,i)
        mtop=mtop-dh
        amount1=newlist[-3]
        amount2=newlist[-1]
        totals[0]=totals[0]+float(amount1)
        totals[1]=totals[1]+float(amount2)

        if mtop<bottomy+dh and k+1<l1:
            mtop=0
            rlist=itemslist[k+1:l1]
            return mtop,totals,rlist

    return mtop,totals,0





def custcontents(file4,itemlist,headerlist,pstops,cache):

    today = datetime.datetime.today().strftime('%m/%d/%Y')
    invodate = datetime.date.today().strftime('%m/%d/%Y')
    sdate=request.values.get('start')
    fdate=request.values.get('finish')
    openbalrequest=request.values.get('dc6')
    print('itemlist=',itemlist)

    try:
        start=datetime.datetime.strptime(sdate, '%Y-%m-%d')
        end=datetime.datetime.strptime(fdate, '%Y-%m-%d')
    except:
        start=today
        end=today

    ltm,rtm,bump,tb,ctrall,left_ctr,right_ctr,dl,dh,tdl,hls,m1,m2,m3,m4,m5,m6,m7,n1,n2,n3=reportsettings(1)
    mtop = n1

    pages=[file4]
    page=1
    c=canvas.Canvas(file4, pagesize=letter)
    c.setLineWidth(1)
    bottomy=n3
    complete=0
    ptot=0.0
    for p in pstops:
        ptot=ptot+p
    tofromavail=220-(ptot-140)
    tfeach=tofromavail/2.0

    pvec=[55]+pstops+[tfeach,tfeach,40,40]
    hvec=[ltm]
    base=ltm
    for p in pvec:
        base=base+p
        hvec.append(base)
    hvec.append(rtm)

    p1=ltm+55
    p2=ltm+120
    p3=ltm+190
    p4=ltm+300
    p5=rtm-120
    p6=rtm-80
    p7=rtm-40


    totals=[0.0,0.0]

    while complete==0 and page<20:

        #hvec=[ltm,p1,p2,p3,p4,p5,p6,p7,rtm]
        #headerlist=['InvoDate', 'Order','Container','From','To','Invoiced','Paid','Open']
        keylen=5-(11-len(headerlist))
        justify=['c']+['l']*keylen+['l','l','r','r','r']
        mtop=stripheader(c,10,mtop,hvec,headerlist)

        mtop,totals,rlist=orderlisting(c,9,mtop,hvec,itemlist,justify,totals,bottomy)
        if mtop>0:
            complete=1
        else:
            c,page,pages,mtop=newpagecheck(c,mtop,bottomy+20,page,file4,pages)
            itemlist=rlist

    if openbalrequest!='on':
        c.setFont('Helvetica-Bold',12,leading=None)
        c.drawRightString(rtm-bump,bottomy+dl*1.2+bump,'Income Total: '+dollar(totals[0]))

    c.setFont('Helvetica-Bold',12,leading=None)
    c.drawRightString(rtm-bump,bottomy+bump,'Open Balance Total: '+dollar(totals[1]))

    c.showPage()
    c.save()

    if len(pages)>1:
        pdfcommand=['pdfunite']
        for page in pages:
            pdfcommand.append(page)
        multioutput=addpath(f'tmp/{scac}/data/vreport/multioutput'+str(cache)+'.pdf')
        pdfcommand.append(multioutput)
        tes=subprocess.check_output(pdfcommand)
    else:
        multioutput=''

    return pages,multioutput

def pl_orderlisting(c,fsize,mtop,hvec,itemslist,justify,totals,bottomy,kval,optype,details):
    c.setFont('Helvetica-Bold',fsize,leading=None)
    l1=len(itemslist)
    jtypes=['T','O','S','M']
    dl=fsize*2
    dh=dl*.6
    bump=2.5
    sb=2
    if details=='on':
        mtop = mtop-dh

    ctr=[]
    for j,hpt in enumerate(hvec):
        if j<len(hvec)-1:
            ctr.append(avg(hpt,hvec[j+1]))

    if l1==0:
        c.drawString(hvec[4],mtop,'No Items Reported This Period')
        mtop=mtop-dh

    for k in range(l1):
        newlist=itemslist[k]
        jtype=newlist[1]
        amount=newlist[-1]
        if jtype==jtypes[kval]:
            totals[kval]=totals[kval]+float(amount)
            if details=='on':
                for j,i in enumerate(newlist):
                    if justify[j]=='l':
                        c.drawString(hvec[j]+sb,mtop,i)
                    elif justify[j]=='c':
                        c.drawCentredString(ctr[j],mtop,i)
                    else:
                        c.drawRightString(hvec[j+1]-sb,mtop,i)
                mtop=mtop-dh


        if mtop<bottomy+dh and k+1<l1:
            mtop=0
            rlist=itemslist[k+1:l1]
            return mtop,totals,rlist

    return mtop,totals,0

def pl_explisting(c,fsize,mtop,hvec,itemslist,justify,totals,bottomy,kval,exp,details,catbp):
    c.setFont('Helvetica-Bold',fsize,leading=None)
    l1=len(itemslist)
    dl=fsize*2
    dh=dl*.6
    bump=2.5
    sb=2
    if details=='on':
        mtop = mtop-dh

    ctr=[]
    for j,hpt in enumerate(hvec):
        if j<len(hvec)-1:
            ctr.append(avg(hpt,hvec[j+1]))

    if l1==0:
        c.drawString(hvec[4],mtop,'No Items Reported This Period')
        mtop=mtop-dh

    for k in range(l1):
        newlist=itemslist[k]
        jtype=newlist[1]
        amount=newlist[-1]
        if jtype==exp:
            prorated=float(amount)*catbp[kval]
            totals[kval]=totals[kval]+prorated
            if catbp[kval]<1.0:
                newlist[-1]='*pr*'+d2s(prorated)
            if details=='on':
                for j,i in enumerate(newlist):
                    if justify[j]=='l':
                        c.drawString(hvec[j]+sb,mtop,i)
                    elif justify[j]=='c':
                        c.drawCentredString(ctr[j],mtop,i)
                    else:
                        c.drawRightString(hvec[j+1]-sb,mtop,i)
                mtop=mtop-dh


        if mtop<bottomy+dh and k+1<l1:
            mtop=0
            rlist=itemslist[k+1:l1]
            return mtop,totals,rlist

    return mtop,totals,0


def plcontents(file4,itemlist,blist,cache):

    details=request.values.get('dt3')
    indent1=50
    lastexp='D'
    today = datetime.datetime.today().strftime('%m/%d/%Y')
    invodate = datetime.date.today().strftime('%m/%d/%Y')
    sdate=request.values.get('start')
    fdate=request.values.get('finish')
    try:
        start=datetime.datetime.strptime(sdate, '%Y-%m-%d')
        end=datetime.datetime.strptime(fdate, '%Y-%m-%d')
    except:
        start=today
        end=today

    ltm,rtm,bump,tb,ctrall,left_ctr,right_ctr,dl,dh,tdl,hls,m1,m2,m3,m4,m5,m6,m7,n1,n2,n3=reportsettings(1)

    pages=[file4]
    page=1
    c=canvas.Canvas(file4, pagesize=letter)
    c.setLineWidth(1)
    bottomy=n3

    mtop=n1

    p1=ltm+55
    p15=ltm+65
    p2=ltm+140
    p3=ltm+200
    p4=ltm+270
    p5=rtm-150
    p6=rtm-50
#    p7=rtm-40

    #Set the Building Propration for Items shared between FEL and Other
    Fbp=.80
    prorate=[1.0,1.0]
    inctotals=[0.0,0.0,0.0,0.0]
    optype=['Trucking','Overseas','Storage','Moving']
    keyval=['Order','Booking','JO','JO']
    exptotals=[0.0,0.0]
    i_categories=['BldRent','BldRepMaint','Utilities','Adv-Mark','BankFees','Taxes','OfficeSupp','Insurance','ProfFees','Other']
    d_categories=['Container','Towing','Fuel','Payroll','Rentals','Other']
    catbp=[1.0,1.0,1.0,1.0,1.0,1.0,Fbp,Fbp,Fbp,1.0,1.0,1.0,Fbp,1.0,1.0,1.0]
    extype=[]
    exptotals=[]
    for cat in d_categories:
        extype.append('D:'+cat)
        exptotals.append(0.0)
    for cat in i_categories:
        extype.append('I:'+cat)
        exptotals.append(0.0)

#___________Income_____________________________
    for kval in range(4):

        complete=0
        while complete==0 and page<20:
            c,page,pages,mtop=newpagecheck(c,mtop,bottomy+20,page,file4,pages)
            if details=='on':
                hvec=[ltm,p1,p15,p2,p3,p4,p5,p6,rtm]
                headerlist=['InvoDate', 'L', 'Service',optype[kval],'Container','From','To','Invoiced']
                justify=['c','c','l','l','l','l','l','r']
                mtop=stripheader(c,10,mtop,hvec,headerlist)
            elif mtop==n1:
                hvec=[ltm,rtm]
                headerlist=['INCOME ALL SOURCES']
                justify=['r']
                mtop=stripheader(c,12,mtop,hvec,headerlist)
                mtop=mtop-dh*1.5

            mtop,inctotals,rlist=pl_orderlisting(c,9,mtop,hvec,itemlist,justify,inctotals,bottomy,kval,optype,details)
            if mtop>0:
                complete=1
            else:
                c,page,pages,mtop=newpagecheck(c,mtop,bottomy+20,page,file4,pages)
                itemlist=rlist

        if details=='on':
            mtop=mtop-dh
            indent=0
        else:
            indent=indent1
        c.setFont('Helvetica-Bold',11,leading=None)
        if kval==0:
            c.drawString(ltm+indent,mtop,'Income from:')
        c.drawRightString(rtm-bump-indent*3,mtop,optype[kval]+' Operations:')
        c.drawRightString(rtm-bump-indent,mtop,dollar(inctotals[kval]))
        mtop=mtop-dh*1.2

    inctotal=0.0
    for i in inctotals:
        inctotal=inctotal+i

    c.setFont('Helvetica-Bold',11,leading=None)
    #mtop=mtop-dh
    c.drawRightString(rtm-bump-indent*2,mtop,'Total for All Sources of Income:')
    c.drawRightString(rtm-bump,mtop,dollar(inctotal))
    mtop=mtop-dh

    p1=ltm+55
    p2=ltm+120
    p3=ltm+240
    p4=ltm+410
    p5=rtm-120
    p6=rtm-50
#___________Expenses_____________________________
    for kval,exp in enumerate(extype):
#blist.append([d1.strftime('%m/%d/%Y'),'COGS',company,desc,acct,nodollar(bamount)])
        complete=0
        count=0
        while complete==0 and page<20 and count<5000:

            count+=1
            c,page,pages,mtop=newpagecheck(c,mtop,bottomy+20,page,file4,pages)
            if details=='on':
                hvec=[ltm,p1,p2,p3,p5,p6,rtm]
                headerlist=['BillDate','ExpType','Vendor','Description','Account','Expense']
                justify=['c','c','l','l','l','r']
                mtop=stripheader(c,10,mtop,hvec,headerlist)
            elif mtop==n1 or kval==0:
                hvec=[ltm,rtm]
                headerlist=['COSTS and EXPENSES']
                justify=['r']
                mtop=stripheader(c,12,mtop,hvec,headerlist)
                mtop=mtop-dh*1.5

            mtop,exptotals,rlist=pl_explisting(c,9,mtop,hvec,blist,justify,exptotals,bottomy,kval,exp,details,catbp)
            if mtop>0:
                complete=1
            else:
                c,page,pages,mtop=newpagecheck(c,mtop,bottomy+20,page,file4,pages)
                blist=rlist

        if details=='on':
            mtop=mtop-dh
            indent=0
        else:
            indent=indent1

        c.setFont('Helvetica-Bold',11,leading=None)

        thisexp=extype[kval][0]
        if thisexp != lastexp:
            dtotals=exptotals[0:kval]
            print(kval,dtotals)
            dtotal=0.0
            for tot in dtotals:
                dtotal=dtotal + tot
            mtop=mtop-dh*.5
            c.drawRightString(rtm-bump,mtop,dollar(dtotal))

            mtop=mtop-2*dh
            lastexp=thisexp
            c.drawString(ltm+indent,mtop,'Indirect Costs (Overhead):')

        if kval==0:
            c.drawString(ltm+indent,mtop,'Direct Costs:')



        catname=extype[kval].replace('D:','').replace('I:','')
        c.drawRightString(rtm-bump-indent*3,mtop,catname+':')
        c.drawRightString(rtm-bump-indent,mtop,dollar(exptotals[kval]))
        mtop=mtop-dh

        if kval==len(extype)-1:
            lastones=len(exptotals)-len(dtotals)
            itotals=exptotals[-lastones:]
            itotal=0.0
            for tot in itotals:
                itotal=itotal + tot
            try:
                gapct=itotal/inctotal*100
            except:
                gapct=0.00
            mtop=mtop-dh*.5
            c.drawString(ltm+indent*2,mtop,'Overhead Rate: '+d2s(gapct)+'%')
            c.drawRightString(rtm-bump,mtop,dollar(itotal))
            mtop=mtop-2*dh

    exptotal=0.0
    for i in exptotals:
        exptotal=exptotal+i

    c.setFont('Helvetica-Bold',11,leading=None)
    c.drawRightString(rtm-bump,mtop,'Total for All Expenses: '+dollar(exptotal))
    mtop=mtop-2*dh

    c.showPage()
    c.save()

    if len(pages)>1:
        pdfcommand=['pdfunite']
        for page in pages:
            pdfcommand.append(page)
        multioutput=addpath(f'tmp/{scac}/data/vreport/multioutput'+str(cache)+'.pdf')
        pdfcommand.append(multioutput)
        tes=subprocess.check_output(pdfcommand)
    else:
        multioutput=''

    return pages,multioutput
