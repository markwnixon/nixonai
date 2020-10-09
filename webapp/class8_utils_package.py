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
from webapp.class8_dicts import Trucking_genre, Orders_setup, Interchange_setup, Customers_setup, Services_setup

from webapp.utils import *
import subprocess
import os
import datetime
from PyPDF2 import PdfFileReader
from webapp.page_merger import pagemergerx
from PIL import Image

def call_stamp(odat, task_iter):
    stampdata = []
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

def stamp_document(genre, odat, stamplist, stampdata, err, docin):
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

    document_stamps = eval(f"{genre}_genre['image_stamps']")
    document_signatures = eval(f"{genre}_genre['signature_stamps']")
    doc_stamps, doc_signatures = [], []
    for key in document_stamps:
        doc_stamps.append(key)
    for key in document_signatures:
        doc_signatures.append(key)
    print('the stamplist is:', stamplist)
    print('the stampdata is:', stampdata)

    for jx, stamp in enumerate(stamplist):
        stampname = stampdata[7*jx + 5]
        print('stampname is:',stampname)
        if stampname in doc_stamps:
            listdata = document_stamps[stampname]
        if stampname in doc_signatures:
            listdata = document_signatures[stampname]
        stampfile = listdata[0]
        stampfolder = listdata[1]
        filepath = addpath(f'static/{scac}/data/{stampfolder}/{stampfile}')
        stamp_page = stampdata[7*jx]
        stamp_up = stampdata[7*jx + 1]
        stamp_right = stampdata[7*jx + 2]
        stamp_scale = stampdata[7*jx + 3]

        # Want to create a signature/date doc page
        file2 = addpath(f'static/{scac}/data/processing/t1.pdf')
        c = canvas.Canvas(file2, pagesize=letter)
        c.setLineWidth(1)
        stamp_page = stamp_page - 1
        image = Image.open(filepath)
        imsize_list = list(image.size)
        scalesize = [0,0]
        scalesize[0] = int(stamp_scale * imsize_list[0])
        scalesize[1] = int(stamp_scale * imsize_list[1])
        newsize = tuple(scalesize)
        print(newsize)
        new_image = image.resize(newsize)
        new_filepath = addpath(f'static/{scac}/data/{stampfolder}/{stampfile}_{scalesize[0]}_{scalesize[1]}.png')
        print(new_filepath)
        new_image.save(new_filepath)
        c.drawImage(new_filepath, stamp_right, stamp_up, mask='auto')
        c.showPage()
        c.save()
        cache = 1
        sigpagefile = addpath(f'static/{scac}/data/vreport/' + str(stamp_page + 1) + '.pdf')
        cache, docrefx = pagemergerx([file1, file2], stamp_page, cache)
        file3 = addpath(f'static/{scac}/data/vreport/report1.pdf')
        os.remove(sigpagefile)
        os.rename(file3, sigpagefile)
        repackage(npages, file6, docin)

    # Create final document after all the stamp applied:
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
                fa = addpath(f'static/{scac}/data/vorders/{odat.Proof}')
                print('Looking for proof file:', fa)
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



def makepackage(genre, odat, task_iter, document_types, stamplist, stampdata, eprof, err):
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
    #stampdata = call_stamp(odat, task_iter)
    fexist, packitems = get_doclist(odat, dockind)


    # Get the email data also in case changes occur there
    emaildata = [0] * 7
    for i in range(7):
        emaildata[i] = request.values.get('edat' + str(i))

    print('packitems final:', packitems)
    print('stampdata final:', stampdata)

    if len(packitems) >= 1:
        pdflist = ['pdfunite'] + packitems + [addpath(docref)]
        tes = subprocess.check_output(pdflist)
    else:
        err.append('No documents available for this selection')

    stampnow = request.values.get('stampnow')
    if stampnow is not None:
        print(f'stamping document going in: {docref}')
        docref = stamp_document(genre, odat, stamplist, stampdata, err, docref)
        print(f'stamped document coming out: {docref}')

    return stampdata, dockind, docref, err, fexist
