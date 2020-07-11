#Now lets print the report out
from flask import session, logging, request
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.pagesizes import landscape
from reportlab.platypus import Image
from reportlab.lib.units import inch
from webapp.viewfuncs import nonone, nononef, nononestr, dollar, avg, comporname, fullname, address, newjo
import csv
import math
import datetime
from webapp.CCC_system_setup import myoslist, addpath, addtxt, bankdata, scac
from webapp.report_background import invobackground, ticketbackground, custbackground
from webapp.page_merger import pagemerger,pagemergermp
from webapp.report_headers import jayheaders, ticketheaders, custheaders, plheaders
from webapp.report_data import jaycalcs,ticketcalcs,incomecalcs, custcalcs, plcalcs, depositcalcs
from webapp.report_content import jaycontents,ticketcontents, incomecontents, custcontents, plcontents, depositcontents
from webapp import db
from webapp.models import Income, Accounts, JO
import shutil

def reportmaker(type,thiscomp):

    cache = request.values.get('cache')
    cache=nonone(cache)

    file2=addpath(f'tmp/{scac}/data/vreport/background.pdf')
    file3=addpath(f'tmp/{scac}/data/vreport/headers.pdf')
    file4=addpath(f'tmp/{scac}/data/vreport/contents.pdf')
    qnote, note, bank, us, lab, logoi = bankdata('FC')
    file1=addpath(f'tmp/{scac}/data/vreport/pagestart.pdf')

    c=canvas.Canvas(file1, pagesize=letter)
    c.setLineWidth(1)
    #logo = addpath("static/pics/logo3.jpg")
    c.drawImage(logoi, 185, 680, mask='auto')
    c.showPage()
    c.save()

    if type=='mtick':
        ticketbackground(file2)
        ticketheaders(file3)
        itemlist=ticketcalcs()
        ticketcontents(file4,itemlist)
        cache,docref=pagemerger([file1,file2,file3,file4],cache)

    if type=='jay':
        invobackground(file2)
        jayheaders(file3)
        paiditems,servicelist,itemlist,bitemlist,total,btotal,nettotal=jaycalcs()
        pages,multioutput=jaycontents(file4,paiditems,servicelist,itemlist,bitemlist,total,btotal,nettotal,cache)
        if len(pages)>1:
            cache,docref=pagemergermp([file1,file2,file3],cache,pages,multioutput)
        else:
            cache,docref=pagemerger([file1,file2,file3,file4],cache)

    if type=='income':
        ticketbackground(file2)
        ticketheaders(file3)
        itemlist=incomecalcs()
        pages,multioutput=incomecontents(file4,itemlist,cache)
        if len(pages)>1:
            cache,docref=pagemergermp([file1,file2,file3],cache,pages,multioutput)
        else:
            cache,docref=pagemerger([file1,file2,file3,file4],cache)

    if type=='expenses':
        ticketbackground(file2)
        ticketheaders(file3)
        itemlist=incomecalcs()
        pages,multioutput=incomecontents(file4,itemlist,cache)
        if len(pages)>1:
            cache,docref=pagemergermp([file1,file2,file3],cache,pages,multioutput)
        else:
            cache,docref=pagemerger([file1,file2,file3,file4],cache)

    if type=='customer':
        custbackground(file2)
        custheaders(file3,thiscomp)
        print('thiscompany=',thiscomp)
        itemlist,headerlist,pstops=custcalcs(thiscomp)
        pages,multioutput=custcontents(file4,itemlist,headerlist,pstops,cache)
        if len(pages)>1:
            cache,docref=pagemergermp([file1,file2,file3],cache,pages,multioutput)
        else:
            cache,docref=pagemerger([file1,file2,file3,file4],cache)

    if type=='pl':
        custbackground(file2)
        plheaders(file3)
        itemlist,blist=plcalcs()
        pages,multioutput=plcontents(file4,itemlist,blist,cache)
        if len(pages)>1:
            cache,docref=pagemergermp([file1,file2,file3],cache,pages,multioutput)
        else:
            cache,docref=pagemerger([file1,file2,file3,file4],cache)

    if type=='deposit' or type=='recdeposit':


        if type=='recdeposit':
            stamp=1
        else:
            stamp=0
        file2=addpath(f'tmp/{scac}/data/vreport/depositslip.pdf')
        print('thiscomp=',thiscomp)
        itemlist=depositcalcs(thiscomp)
        # We are creating a deposit for review so get the account to deposit into
        depojo = request.values.get('depojo')
        acdeposit = request.values.get('acdeposit')
        print(itemlist,depojo)
        pages,multioutput=depositcontents(file4,itemlist,cache,depojo,acdeposit,stamp)
        cache,docref=pagemerger([file4,file2,file1],cache)

        if stamp == 1:
            savefile = addpath(f'tmp/{scac}/data/vdeposits/' + depojo + '.pdf')
            shutil.copyfile(addpath(docref), savefile)

    return cache,docref
