from flask import request
from webapp import db
from webapp.models import People, Drops, Drivers, Vehicles
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.pdfmetrics import stringWidth
import datetime
import shutil
from webapp.viewfuncs import parseline, parselinenoupper
from webapp.CCC_system_setup import addpath, bankdata, scac
from webapp.class8_utils_invoice import scroll_write, center_write, write_lines
from webapp.class8_utils_email import emaildata_update
from webapp.utils import *
import subprocess
import os
import datetime
from PyPDF2 import PdfFileReader
from webapp.page_merger import pagemergerx
from PIL import Image

def call_stamp(odat, task_iter):
    stampdata = [3, 35, 35, 1,5, 120, 100, 1, 5, 477, 350, 12]
    if task_iter > 1:
        for i in range(12):
            stampdata[i] = request.values.get(f'stampdata{i}')
    else:
        stampstring = odat.Status
        if isinstance(stampstring, str):
            print('stampstring is:', stampstring)
            stampdata = json.loads(stampstring)
            if isinstance(stampdata, list):
                print('json loads stampdata is', stampdata)
                if None in stampdata: stampdata = [0]*12
            else: stampdata = [3, 35, 35, 1,5, 120, 100, 1, 5, 477, 350, 12]
    return stampdata

def repackage(npages,file6,docref):
    newpages = []
    for f in range(1, npages+1):
        newpages.append(addpath(f'static/{scac}/data/vreport/'+str(f)+'.pdf'))
    pdfcommand = ['pdfunite']
    for page in newpages:
        pdfcommand.append(page)
    pdfcommand.append(file6)
    tes = subprocess.check_output(pdfcommand)
    os.rename(file6, addpath(docref))

def stamp_document(odat, stampdata, document_stamps, document_signatures, err, docin):
    # if stampnow is called the document will already be recreated as a blank for here
    # and the information includes odat, pdat, idata
    err.append('Review Signed Package')
    cache2 = int(odat.Pkcache)
    docref = f'/static/{scac}/data/vpackages/P_c{cache2}_{odat.Jo}.pdf'
    docreturn = f'static/{scac}/data/vpackages/P_c{cache2}_{odat.Jo}.pdf'
    odat.Package = f'P_c{cache2}_{odat.Jo}.pdf'
    db.session.commit()

    today = datetime.datetime.today()
    year = str(today.year)
    day = str(today.day)
    month = str(today.month)
    # print(month,day,year)
    datestr = month + '/' + day + '/' + year
    file1 = addpath(docin)
    reader = PdfFileReader(open(file1, 'rb'))
    npages = reader.getNumPages()
    ck = subprocess.check_output(['pdfseparate', file1, addpath(f'static/{scac}/data/vreport/%d.pdf')])
    file6 = addpath(f'static/{scac}/data/vreport/report6.pdf')


    xpage = int(stampdata[0])
    xmarkx = int(stampdata[2])
    xmarky = int(stampdata[1])
    xscale = float(stampdata[3])
    datepage = int(stampdata[8])
    datex = int(stampdata[10])
    datey = int(stampdata[9])
    datefont = int(stampdata[11])

    signature = request.values.get('sigstamp')
    if signature != None:
            sigcheck = request.values.get('sigcheck')
            if sigcheck:
                sigpage = int(request.values.get('sigpage'))
                sigx = int(request.values.get('sigx'))
                sigy = int(request.values.get('sigy'))
                sigscale = float(request.values.get('sigscale'))
                # Want to create a signature/date doc page
                file2 = addpath(f'static/{scac}/data/processing/t1.pdf')
                c = canvas.Canvas(file2, pagesize=letter)
                c.setLineWidth(1)
                sigpage = sigpage - 1
                sig = addpath(f'static/{scac}/pics/marksign2.jpg')
                image = Image.open(sig)
                imsize_list = list(image.size)
                scalesize = imsize_list
                scalesize[0] = int(sigscale*scalesize[0])
                scalesize[1] = int(sigscale*scalesize[1])
                newsize = tuple(scalesize)
                print(newsize)
                new_image = image.resize(newsize)
                signew = addpath(f'static/{scac}/pics/marksign2_{scalesize[0]}{scalesize[1]}.png')
                new_image.save(signew)
                c.drawImage(signew, sigx, sigy, mask='auto')
                c.showPage()
                c.save()
                cache = 1
                sigpagefile = addpath(f'static/{scac}/data/vreport/' + str(sigpage + 1) + '.pdf')
                cache, docrefx = pagemergerx([file1, file2], sigpage, cache)
                file3 = addpath(f'static/{scac}/data/vreport/report1.pdf')
                os.remove(sigpagefile)
                os.rename(file3, sigpagefile)
                repackage(npages, file6, docin)

    if datepage > 0:
        # Want to create a signature/date doc page
        datepage = datepage - 1
        file2 = addpath(f'static/{scac}/data/processing/t1.pdf')
        c = canvas.Canvas(file2, pagesize=letter)
        c.setLineWidth(1)
        c.setFont('Helvetica', datefont, leading=None)
        c.drawString(datex, datey, datestr)
        c.showPage()
        c.save()
        cache = 1
        datepagefile = addpath(f'static/{scac}/data/vreport/' + str(datepage + 1) + '.pdf')
        cache, docrefx = pagemergerx([file1, file2], datepage, cache)
        file3 = addpath(f'static/{scac}/data/vreport/report1.pdf')
        os.remove(datepagefile)
        os.rename(file3, datepagefile)
        repackage(npages, file6, docin)

    if xpage > 0:
        xpage = xpage - 1
        xpagefile = addpath(f'static/{scac}/data/vreport/' + str(xpage + 1) + '.pdf')
        file2 = addpath(f'static/{scac}/data/processing/t2.pdf')
        c = canvas.Canvas(file2, pagesize=letter)
        c.setLineWidth(1)
        xbox = addpath(f'static/{scac}/pics/x100.png')
        image = Image.open(xbox)
        imsize_list = list(image.size)
        scalesize = imsize_list
        scalesize[0] = int(xscale*scalesize[0])
        scalesize[1] = int(xscale*scalesize[1])
        newsize = tuple(scalesize)
        print(newsize)
        new_image = image.resize(newsize)
        xboxnew = addpath(f'static/{scac}/pics/x100_{scalesize[0]}{scalesize[1]}.png')
        new_image.save(xboxnew)
        #c.drawImage(xbox, xmarkx, xmarky, width=30, preserveAspectRatio=True, mask='auto')
        c.drawImage(xboxnew, xmarkx, xmarky, mask='auto')
        c.showPage()
        c.save()
        cache = 5
        cache, docrefx = pagemergerx([file1, file2], xpage, cache)
        file5 = addpath(f'static/{scac}/data/vreport/report5.pdf')
        os.remove(xpagefile)
        os.rename(file5, xpagefile)
        repackage(npages, file6, docin)
    # Create final document after all the overwrites:
    os.rename(addpath(docin), addpath(docref))
    odat.Pkcache = cache2 + 1
    db.session.commit()

    return docreturn


def get_doclist(odat, dockind):
    fexist = [0] * 4
    packitems = []
    for jx, thisdoc in enumerate(dockind):
        if thisdoc != '0':
            if thisdoc == 'Source':
                fa = addpath(f'static/{scac}/data/vorders/{odat.Source}')
                if os.path.isfile(fa):
                    packitems.append(fa)
                    fexist[jx] = 1
            if thisdoc == 'Invoice':
                fa = addpath(f'static/{scac}/data/vinvoice/{odat.Invoice}')
                if os.path.isfile(fa):
                    packitems.append(fa)
                    fexist[jx] = 1
            if thisdoc == 'Proofs':
                fa = addpath(f'static/{scac}/data/vproofs/{odat.Proof}')
                if os.path.isfile(fa):
                    packitems.append(fa)
                    fexist[jx] = 1
            if thisdoc == 'Ticks':
                idata = Interchange.query.filter(Interchange.Container == odat.Container).all()
                if idata is not None:
                    if len(idata) > 1:
                        # Get a blended ticket
                        con = idata[0].Container
                        newdoc = f'static/{scac}/data/vinterchange/{con}_Blended.pdf'
                        if os.path.isfile(addpath(newdoc)):
                            print(f'{newdoc} exists already')
                        else:
                            g1 = f'static/{scac}/data/vinterchange/{idata[0].Original}'
                            g2 = f'static/{scac}/data/vinterchange/{idata[1].Original}'
                            blendticks(addpath(g1), addpath(g2), addpath(newdoc))
                        packitems.append(addpath(newdoc))
                        fexist[jx] = 1
                    else:
                        packitems.append(addpath(f'tmp/{scac}/data/vinterchange/{idata[0].Original}'))
                        fexist[jx] = 1
    return fexist, packitems



def makepackage(odat, task_iter, document_types, document_stamps, document_signatures, eprof, err):
    err = []
    dockind = ['']*4
    if task_iter > 1 and eprof == 'Custom':
        sections = ['1st Section', '2nd Section', '3rd Section', '4th Section']
        for jx, section in enumerate(sections): dockind[jx] = request.values.get(section)
    else:
        dockind = document_types[eprof]
    print('dockind=',dockind)
    try:
        cache2 = int(odat.Pkcache) + 1
    except:
        cache2 = 1
    basefile = f'P_c{cache2}_{odat.Jo}.pdf'
    odat.Package = basefile
    odat.Pkcache = cache2
    db.session.commit()
    docref = f'static/{scac}/data/vpackages/{basefile}'

    #stampdata defines marks we want to add to the document and their location
    #emaildata comes from the email profile but can be amended here
    #packitems are the items chosen to be included in the package
    #doclist are the items available to be added to the package
    #dockind is the kind of documents we want for this package
    stampdata = call_stamp(odat, task_iter)
    fexist, packitems = get_doclist(odat, dockind)


    # Get the email data also in case changes occur there
    emaildata = [0] * 7
    for i in range(7):
        emaildata[i] = request.values.get('edat' + str(i))

    print('packitems final:', packitems)
    print('stampdata final:', stampdata)
    stampstring = json.dumps(stampdata)
    odat.Status = stampstring
    db.session.commit()

    if len(packitems) >= 1:
        pdflist = ['pdfunite'] + packitems + [addpath(docref)]
        tes = subprocess.check_output(pdflist)
    else:
        err.append('No documents available for this selection')

    stampnow = request.values.get('stampnow')
    if stampnow is not None:
        print(f'stamping document going in: {docref}')
        docref = stamp_document(odat, stampdata, document_stamps, document_signatures, err, docref)
        print(f'stamped document coming out: {docref}')

    return stampdata, dockind, docref, err, fexist
