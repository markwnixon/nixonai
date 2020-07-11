from flask import session, logging, request
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.pagesizes import landscape
from reportlab.platypus import Image
from reportlab.lib.units import inch
from webapp.viewfuncs import nonone, nononef, nononestr, dollar, avg, comporname, fullname, address
import csv
import math
import datetime
from webapp.report_content import reportsettings

def ticketheaders(file3):
    
    today = datetime.datetime.today().strftime('%m/%d/%Y')
    invodate = datetime.date.today().strftime('%m/%d/%Y')
    sdate=request.values.get('start')
    fdate=request.values.get('finish')
    ltm,rtm,bump,tb,ctrall,left_ctr,right_ctr,dl,dh,tdl,hls,m1,m2,m3,m4,m5,m6,m7,n1,n2,n3=reportsettings(1)
    
    dateline=m1+8.2*dl
    mtmp=dateline-3.5*dl
    level1=mtmp+3.5*dl
    
    c=canvas.Canvas(file3, pagesize=letter)
    c.setLineWidth(1)
    
    #Draw header with separators
    line2=['Date', 'Booking','Container','Type','Tag','Driver']
    place=[ltm+10,ltm+100,ltm+180,ltm+280,ltm+370,rtm-100]
    place2=[ltm,ltm+100,ltm+180,ltm+280,ltm+370,rtm-100,rtm]
    ctr=[]
    for j,p in enumerate(place):
        ctr.append(avg(place2[j]-10,place2[j+1]-10))
            
    c.setFont('Helvetica-Bold',10,leading=None)
    for j, i in enumerate(line2):
        c.drawCentredString(ctr[j],n2+tb,i)
    
    for k in place:
        c.line(k-10,n1,k-10,n2)
        
    c.setFont('Helvetica-Bold',24,leading=None)
    c.drawCentredString(rtm-75,dateline+1.5*dl,'Report')
                  
    c.setFont('Helvetica-Bold',12,leading=None)    
    c.drawString(ltm+bump*3,level1+bump*2,'Unmatched Interchange Ticket Report')
    c.setFont('Helvetica',12,leading=None)
    c.drawCentredString(rtm-112.5,dateline+bump,'Created')
    c.drawCentredString(rtm-37.7,dateline+bump,'Type')

    dh=13
    top=level1-dh
    lft=ltm+bump*3
    billto=list(range(5))
    billto[0]='Explanation:  This report summarizes'
    billto[1]='the unmatched tickets from interchange.'
    billto[2]='We need the matching tickets to those'
    billto[3]='shown (if have Empty-Out then we need'
    billto[4]='the Load-In, for example)'
    for i in billto:
        c.drawString(lft,top,i)
        top=top-dh
            
    x=avg(rtm-75,rtm)
    y=dateline-dh-bump
    c.drawCentredString(x,y,'Interchange')
    x=avg(rtm-75,rtm-150)
    c.drawCentredString(x,y,invodate)

    drangestring='Date Range: '+sdate+' to '+fdate
    c.drawRightString(rtm-bump,y-30,drangestring)
    
    c.showPage()
    c.save()


def jayheaders(file3):
    
    today = datetime.datetime.today().strftime('%m/%d/%Y')
    invodate = datetime.date.today().strftime('%m/%d/%Y')
    sdate=request.values.get('start')
    fdate=request.values.get('finish')

    billto=list(range(5))
    billto[0]='First Eagle Logistics'
    billto[1]='505 Hampton Park Blvd Unit O'
    billto[2]='Capitol Heights, MD  20743'
    billto[3]='301-516-3000'
    billto[4]='info@firsteaglelogistics.com'
    
    ltm,rtm,bump,tb,ctrall,left_ctr,right_ctr,dl,dh,tdl,hls,m1,m2,m3,m4,m5,m6,m7,n1,n2,n3=reportsettings(1)

    c=canvas.Canvas(file3, pagesize=letter)
    c.setLineWidth(1)
    
    #Draw header separators
    p1=ltm+50
    p2=p1+50
    p3=p2+80
    p4=p3+70
    p5=rtm-132
    p7=rtm-100
    p8=rtm-70
    p9=rtm-40
    
    dateline=m1+8.2*dl
    
    #sds1  =[p1,p2,p3,p4,p5,p7,p8,p9]    
    #for k in sds1:
        #c.line(k,n1,k,n2)

    c.setFont('Helvetica-Bold',24,leading=None)
    c.drawCentredString(rtm-75,dateline+1.5*dl,'Invoice')
    
    c.setFont('Helvetica',12,leading=None)
    c.drawCentredString(rtm-112.5,dateline+bump,'Created')
    c.drawCentredString(rtm-37.7,dateline+bump,'Invoice #')

    #Main Items Header
    #c.setFont('Helvetica-Bold',10,leading=None)
    #ctr=[avg(ltm,p1),avg(p1,p2),avg(p2,p3),avg(p3,p4),avg(p4,p5),avg(p5,p7),avg(p7,p8),avg(p8,p9),avg(p9,rtm)]
    #for j,i in enumerate(line2):
    #    c.drawCentredString(ctr[j],n2+tb,i)
                
    c.setFont('Helvetica',12,leading=None)
    
    ctm=218
    mtmp=dateline-3.5*dl
    level1=mtmp+3.5*dl
    c.rect(ltm, dateline-4*dl,175,5*dl, stroke=1, fill=0)
    level1=mtmp+3.5*dl
    c.line(ltm,level1,ltm+175,level1)
    c.drawString(ltm+bump*3,level1+bump*2,'Bill To')

    dh=13
    top=level1-dh
    lft=ltm+bump*3
    for i in billto:
        c.drawString(lft,top,i)
        top=top-dh
            
    x=avg(rtm-75,rtm)
    y=dateline-dh-bump
    c.drawCentredString(x,y,'JayBill')
    x=avg(rtm-75,rtm-150)
    c.drawCentredString(x,y,invodate)

    drangestring='Date Range: '+sdate+' to '+fdate
    c.drawRightString(rtm-bump,y-30,drangestring)
    
    #Date and JO boxes
    
    c.rect(rtm-150,m1+7*dl,150,2*dl,stroke=1,fill=0)
    c.line(rtm-150,dateline,rtm,dateline)
    c.line(rtm-75,m1+7*dl,rtm-75,m1+9*dl)
    
    c.showPage()
    c.save()
    
def custheaders(file3,thiscomp):
    
    today = datetime.datetime.today().strftime('%m/%d/%Y')
    invodate = datetime.date.today().strftime('%m/%d/%Y')
    sdate=request.values.get('start')
    fdate=request.values.get('finish')
    ltm,rtm,bump,tb,ctrall,left_ctr,right_ctr,dl,dh,tdl,hls,m1,m2,m3,m4,m5,m6,m7,n1,n2,n3=reportsettings(1)

    dateline=m1+8.2*dl
    mtmp=dateline-3.5*dl
    level1=mtmp+3.5*dl
    
    c=canvas.Canvas(file3, pagesize=letter)
    c.setLineWidth(1)

    c.setFont('Helvetica-Bold',24,leading=None)
    c.drawCentredString(rtm-75,dateline+1.5*dl,'Report')
                  
    c.setFont('Helvetica-Bold',12,leading=None)    
    c.drawString(ltm+bump*3,level1+bump*2,thiscomp+' Company Report')
    c.setFont('Helvetica',12,leading=None)
    c.drawCentredString(rtm-112.5,dateline+bump,'Created')
    c.drawCentredString(rtm-37.7,dateline+bump,'Type')

    dh=13
    top=level1-dh
    lft=ltm+bump*3
    billto=list(range(5))
    billto[0]='Explanation:  This report summarizes'
    billto[1]='the invoices and income associated'
    billto[2]='with jobs performed for a customer'
    billto[3]=''
    billto[4]=''
    for i in billto:
        c.drawString(lft,top,i)
        top=top-dh
            
    x=avg(rtm-75,rtm)
    y=dateline-dh-bump
    c.drawCentredString(x,y,'Financial')
    x=avg(rtm-75,rtm-150)
    c.drawCentredString(x,y,invodate)

    drangestring='Date Range: '+sdate+' to '+fdate
    c.drawRightString(rtm-bump,y-30,drangestring)
    c.line(rtm-210,y-30-bump,rtm-bump,y-30-bump)
    
    c.showPage()
    c.save()
    
def plheaders(file3):
    
    today = datetime.datetime.today().strftime('%m/%d/%Y')
    invodate = datetime.date.today().strftime('%m/%d/%Y')
    sdate=request.values.get('start')
    fdate=request.values.get('finish')
    ltm,rtm,bump,tb,ctrall,left_ctr,right_ctr,dl,dh,tdl,hls,m1,m2,m3,m4,m5,m6,m7,n1,n2,n3=reportsettings(1)

    dateline=m1+8.2*dl
    mtmp=dateline-3.5*dl
    level1=mtmp+3.5*dl
    
    c=canvas.Canvas(file3, pagesize=letter)
    c.setLineWidth(1)

    c.setFont('Helvetica-Bold',24,leading=None)
    c.drawCentredString(rtm-75,dateline+1.5*dl,'Report')
                  
    c.setFont('Helvetica-Bold',12,leading=None)    
    c.drawString(ltm+bump*3,level1+bump*2,'Profit-Loss Report')
    c.setFont('Helvetica',12,leading=None)
    c.drawCentredString(rtm-112.5,dateline+bump,'Created')
    c.drawCentredString(rtm-37.7,dateline+bump,'Type')

    dh=13
    top=level1-dh
    lft=ltm+bump*3
    billto=list(range(5))
    billto[0]='Explanation:  This report shows company'
    billto[1]='income and expenses by category for'
    billto[2]='the time period requested'
    billto[3]=''
    billto[4]=''
    for i in billto:
        c.drawString(lft,top,i)
        top=top-dh
            
    x=avg(rtm-75,rtm)
    y=dateline-dh-bump
    c.drawCentredString(x,y,'Financial')
    x=avg(rtm-75,rtm-150)
    c.drawCentredString(x,y,invodate)

    drangestring='Date Range: '+sdate+' to '+fdate
    c.drawRightString(rtm-bump,y-30,drangestring)
    c.line(rtm-210,y-30-bump,rtm-bump,y-30-bump)
    
    c.showPage()
    c.save()
