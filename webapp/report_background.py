#Now lets print the report out
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.pagesizes import landscape
from reportlab.platypus import Image
from reportlab.lib.units import inch
from webapp.viewfuncs import nonone, nononef, nononestr, dollar, avg, comporname, fullname, address
import csv
import math
from webapp.report_content import reportsettings

def ticketbackground(file2):
    
    c=canvas.Canvas(file2, pagesize=letter)
    c.setLineWidth(1)
    ltm,rtm,bump,tb,ctrall,left_ctr,right_ctr,dl,dh,tdl,hls,m1,m2,m3,m4,m5,m6,m7,n1,n2,n3=reportsettings(1)

    fulllinesat=[n1,n2,n3]
    
    q1=ltm+180
    q2=rtm-180
    sds3=[q1,q2]

    #Date and JO boxes
    dateline=m1+8.2*dl
    c.rect(rtm-150,m1+7*dl,150,2*dl,stroke=1,fill=0)
    c.line(rtm-150,dateline,rtm,dateline)
    c.line(rtm-75,m1+7*dl,rtm-75,m1+9*dl)

    #Explanation box
    ctm=218
    mtmp=dateline-3.5*dl
    c.rect(ltm, dateline-4*dl,250,5*dl, stroke=1, fill=0)
    level1=mtmp+3.5*dl
    c.line(ltm,level1,ltm+250,level1)

    for i in fulllinesat:
        c.line(ltm,i,rtm,i)

    c.line(ltm,n1,ltm,n3)
    c.line(rtm,n1,rtm,n3)
    
    c.showPage()
    c.save()

def invobackground(file2):
    
    c=canvas.Canvas(file2, pagesize=letter)
    c.setLineWidth(1)
    ltm,rtm,bump,tb,ctrall,left_ctr,right_ctr,dl,dh,tdl,hls,m1,m2,m3,m4,m5,m6,m7,n1,n2,n3=reportsettings(1)

    fulllinesat=[n3]
    
    q1=ltm+180
    q2=rtm-180
    sds3=[q1,q2]

    #Date and JO boxes
    dateline=m1+8.2*dl
    c.rect(rtm-150,m1+7*dl,150,2*dl,stroke=1,fill=0)
    c.line(rtm-150,dateline,rtm,dateline)
    c.line(rtm-75,m1+7*dl,rtm-75,m1+9*dl)

    #Explanation box
    ctm=218
    mtmp=dateline-3.5*dl
    c.rect(ltm, dateline-4*dl,175,5*dl, stroke=1, fill=0)
    level1=mtmp+3.5*dl
    c.line(ltm,level1,ltm+175,level1)

    for i in fulllinesat:
        c.line(ltm,i,rtm,i)

    c.line(ltm,n1,ltm,n3)
    c.line(rtm,n1,rtm,n3)
    
    c.showPage()
    c.save()

def custbackground(file2):
    
    c=canvas.Canvas(file2, pagesize=letter)
    c.setLineWidth(1)
    ltm,rtm,bump,tb,ctrall,left_ctr,right_ctr,dl,dh,tdl,hls,m1,m2,m3,m4,m5,m6,m7,n1,n2,n3=reportsettings(1)

    fulllinesat=[n3]
    
    q1=ltm+180
    q2=rtm-180
    sds3=[q1,q2]

    #Date and JO boxes
    dateline=m1+8.2*dl
    c.rect(rtm-150,m1+7*dl,150,2*dl,stroke=1,fill=0)
    c.line(rtm-150,dateline,rtm,dateline)
    c.line(rtm-75,m1+7*dl,rtm-75,m1+9*dl)

    #Explanation box
    ctm=218
    mtmp=dateline-3.5*dl
    c.rect(ltm, dateline-4*dl,250,5*dl, stroke=1, fill=0)
    level1=mtmp+3.5*dl
    c.line(ltm,level1,ltm+250,level1)

    for i in fulllinesat:
        c.line(ltm,i,rtm,i)

    c.line(ltm,n1,ltm,n3)
    c.line(rtm,n1,rtm,n3)
    
    c.showPage()
    c.save()
