from flask import request
from webapp import db
from webapp.models import People, Drops, Drivers, Vehicles, Interchange
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from PyPDF2 import PdfReader, PdfWriter, Transformation
#from PyPDF2.pdf import PageObject
from reportlab.pdfbase.pdfmetrics import stringWidth
import datetime
import shutil
from webapp.viewfuncs import parseline, parselinenoupper
from webapp.CCC_system_setup import addpath, bankdata, scac
from webapp.class8_utils_invoice import scroll_write, center_write, write_lines
from webapp.class8_utils_email import emaildata_update
from webapp.class8_dicts import Trucking_genre, Orders_setup, Interchange_setup, Customers_setup, Services_setup, Summaries_setup

from webapp.utils import *
import subprocess
import os
import datetime
from PyPDF2 import PdfReader
from webapp.page_merger import pagemergerx
from PIL import Image


NO_PROOF_MARKERS = ['none required', 'no proof needed']


def proof_is_marker(value):
    return str(value or '').strip().lower() in NO_PROOF_MARKERS


def existing_order_pdf(folder, filename):
    if filename is None:
        return ''
    filename = str(filename).strip()
    if not filename or proof_is_marker(filename):
        return ''

    candidates = []
    if os.path.isabs(filename):
        candidates.append(filename)
    if filename.startswith('/static/') or filename.startswith('static/'):
        candidates.append(addpath(filename.lstrip('/')))
    candidates.append(addpath(f'static/{scac}/data/{folder}/{filename}'))
    candidates.append(addpath(f'static/{scac}/data/{folder}/{os.path.basename(filename)}'))

    for filepath in candidates:
        if os.path.isfile(filepath):
            return filepath
    return ''


def order_has_gate_tickets(odat):
    """Gate tickets are normally found through Interchange rows, not Orders.Gate."""
    if existing_order_pdf('vGate', getattr(odat, 'Gate', None)):
        return True

    idata = Interchange.query.filter(Interchange.Container == odat.Container).all()
    if not idata:
        return False

    if len(idata) > 1:
        blended = existing_order_pdf('vGate', f'{idata[0].Container}_Blended.pdf')
        if blended:
            return True
        return bool(existing_order_pdf('vGate', idata[0].Source) and existing_order_pdf('vGate', idata[1].Source))

    return bool(existing_order_pdf('vGate', idata[0].Source))

def call_stamp(odat, task_iter):
    stampdata = []
    if task_iter > 1:
        for i in range(12):
            stampdata[i] = request.values.get(f'stampdata{i}')
    else:
        stampstring = odat.Status
        if isinstance(stampstring, str):
            #print('stampstring is:', stampstring)
            stampdata = json.loads(stampstring)
            if isinstance(stampdata, list):
                #print('json loads stampdata is', stampdata)
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
    docref = f'/static/{scac}/data/vPackage/P_c{cache2}_{odat.Jo}.pdf'
    docreturn = f'static/{scac}/data/vPackage/P_c{cache2}_{odat.Jo}.pdf'
    odat.Package = f'P_c{cache2}_{odat.Jo}.pdf'
    db.session.commit()

    today = datetime.datetime.today()
    year = str(today.year)
    day = str(today.day)
    month = str(today.month)
    # print(month,day,year)
    datestr = month + '/' + day + '/' + year
    file1 = addpath(docin)
    reader = PdfReader(open(file1, 'rb'))
    npages = len(reader.pages)
    ck = subprocess.check_output(['pdfseparate', file1, addpath(f'static/{scac}/data/vreport/%d.pdf')])
    file6 = addpath(f'static/{scac}/data/vreport/report6.pdf')

    document_stamps = eval(f"{genre}_genre['image_stamps']")
    document_signatures = eval(f"{genre}_genre['signature_stamps']")
    doc_stamps, doc_signatures = [], []
    for key in document_stamps:
        doc_stamps.append(key)
    for key in document_signatures:
        doc_signatures.append(key)
    #print('the stamplist is:', stamplist)
    #print('the stampdata is:', stampdata)

    for jx, stamp in enumerate(stamplist):
        stampname = stampdata[7*jx + 5]
        #print('stampname is:',stampname)
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
        #print(newsize)
        new_image = image.resize(newsize)
        new_filepath = addpath(f'static/{scac}/data/{stampfolder}/{stampfile}_{scalesize[0]}_{scalesize[1]}.png')
        #print(new_filepath)
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

def blendticks(gfile1,gfile2,outfile):

    reader1 = PdfReader(open(gfile1, 'rb'))
    p1 = reader1.pages[0]

    reader2 = PdfReader(open(gfile2, 'rb'))
    p2 = reader2.pages[0]

    g3 = addpath(f'static/{scac}/data/vGate/blank.pdf')
    reader3 = PdfReader(open(g3, 'rb'))
    p3 = reader3.pages[0]
    #p2.cropBox.lowerLeft = (50,400)
    #p2.cropBox.upperRight = (600,700)
    #translate first page
    #p3.mergeTranslatedPage(p1, 0, -100, expand=False)
    p1.add_transformation(Transformation().translate(tx=0, ty=-80))
    p3.merge_page(p1)

    #offset_x = p2.mediaBox[2]
    offset_x = 0
    #offset_y = -280
    offset_y = -325

    # add second page to first one
    #p3.mergeTranslatedPage(p2, offset_x, offset_y, expand=False)
    p2.add_transformation(Transformation().translate(tx=offset_x, ty=offset_y))
    p3.merge_page(p2)
    #p3.cropbox.lower_left = (50,250)
    p3.cropbox.lower_left = (50, 150)
    p3.cropbox.upper_right = (550,800)

    output = PdfWriter()
    output.add_page(p3)

    with open(outfile, "wb") as out_f:
        output.write(out_f)

def combine_ticks(gfile1,gfile2,outfile):

    packitems = []
    packitems.append(gfile1)
    packitems.append(gfile2)

    pdflist = ['pdfunite'] + packitems + [outfile]
    tes = subprocess.check_output(pdflist)


def get_doclist(odat, dockind):
    fexist = [0] * 4
    packitems = []
    for jx, thisdoc in enumerate(dockind):
        if thisdoc != '0':
            if thisdoc == 'Source':
                try:
                    fa = existing_order_pdf('vSource', odat.Source)
                    if fa:
                        packitems.append(fa)
                        fexist[jx] = 1
                except:
                    pass
                    #print('No source file exists')
            if thisdoc == 'RateCon':
                try:
                    fa = existing_order_pdf('vRateCon', odat.RateCon)
                    if fa:
                        packitems.append(fa)
                        fexist[jx] = 1
                except:
                    pass
                    #print('No ratecon file exists')
            if thisdoc == 'Invoice':
                try:
                    fa = existing_order_pdf('vInvoice', odat.Invoice)
                    if fa:
                        packitems.append(fa)
                        fexist[jx] = 1
                except:
                    pass
                    #print('No invoice exists')
            if thisdoc == 'Proofs':
                proof_found = False
                try:
                    fa = existing_order_pdf('vProof', odat.Proof)
                    #print('Looking for proof file:', fa)
                    if fa:
                        packitems.append(fa)
                        fexist[jx] = 1
                        proof_found = True
                except:
                    #print('Proof file 1 does not exist')
                    fexist[jx] = 0
                try:
                    fa = existing_order_pdf('vProof', odat.Proof2)
                    #print('Looking for 2nd proof file:', fa)
                    if fa:
                        packitems.append(fa)
                        fexist[jx] = 1
                        proof_found = True
                except:
                    pass
                    #print('Proof file 2 does not exist')
                if not proof_found:
                    try:
                        fa = existing_order_pdf('vProof', odat.DrvProof)
                        # Use driver-uploaded proof only when no standard proof
                        # document exists for the order.
                        if fa:
                            packitems.append(fa)
                            fexist[jx] = 1
                    except:
                        pass

            if thisdoc == 'PaidInvoice':
                try:
                    fa = existing_order_pdf('vPaidInvoice', odat.PaidInvoice)
                    print('Looking for paid invoice file:', fa)
                    if fa:
                        packitems.append(fa)
                        fexist[jx] = 1
                except:
                    pass
                    #print('Paid Invoice does not exist')
            if thisdoc == 'Gate Tickets':
                idata = Interchange.query.filter(Interchange.Container == odat.Container).all()
                if idata:
                    if len(idata) > 1:
                        # Try to get a blended ticket
                        con = idata[0].Container
                        newdoc = f'static/{scac}/data/vGate/{con}_Blended.pdf'
                        if os.path.isfile(addpath(newdoc)):
                            #print(f'{newdoc} exists already')
                            packitems.append(addpath(newdoc))
                            fexist[jx] = 1
                        else:
                            try:
                                g1 = existing_order_pdf('vGate', idata[0].Source)
                                g2 = existing_order_pdf('vGate', idata[1].Source)
                                blendticks(g1, g2, addpath(newdoc))
                                packitems.append(addpath(newdoc))
                                fexist[jx] = 1
                            except:
                                fexist[jx] = 0
                    else:
                        fa = existing_order_pdf('vGate', idata[0].Source)
                        if fa:
                            packitems.append(fa)
                            fexist[jx] = 1
                        else:
                            pass
                            #print('Single gate ticket does not exist')
    return fexist, packitems

def getdocs(odat):
    dockind = []
    #Check for Invoice
    fa = existing_order_pdf('vInvoice', odat.Invoice)
    if fa:
        dockind.append('Invoice')
    #Check for Proof
    fa = existing_order_pdf('vProof', odat.Proof)
    fa2 = existing_order_pdf('vProof', odat.Proof2)
    fa3 = existing_order_pdf('vProof', odat.DrvProof)
    if fa or fa2 or (not fa and not fa2 and fa3):
        dockind.append('Proofs')
    #Check for Gate
    if order_has_gate_tickets(odat):
        dockind.append('Gate Tickets')
    #Check for RateCon
    fa = existing_order_pdf('vRateCon', odat.RateCon)
    if fa:
        dockind.append('RateCon')
    else:
        #If no rate con then try to add DO
        fa = existing_order_pdf('vSource', odat.Source)
        if fa:
            dockind.append('Source')
    ix = len(dockind)
    for jx in range(ix,4): dockind.append('0')

    return dockind




def makepackage(genre, odat, task_iter, document_types, stamplist, stampdata, eprof, err, emaildata):
    err = []
    dockind = ['']*4
    if task_iter > 0 and (eprof == 'Custom' or eprof == 'Custom-Invoice' or eprof == 'Request Rate Con'):
        sections = ['1st Section', '2nd Section', '3rd Section', '4th Section']
        for jx, section in enumerate(sections): dockind[jx] = request.values.get(section)
    else:
        #Set the first iteration based on what is available
        #Gaear towards an invoice package with Invoices, Proof, Gate, RateCon
        dockind = getdocs(odat)
        #dockind = document_types[eprof]
    #print('dockind=',dockind)
    try:
        cache2 = int(odat.Pkcache) + 1
    except:
        cache2 = 1
    oldfile = f'static/{scac}/data/vPackage/{odat.Package}'
    basefile = f'P_c{cache2}_{odat.Jo}.pdf'
    odat.Package = basefile
    odat.Pkcache = cache2
    db.session.commit()
    docref = f'static/{scac}/data/vPackage/{basefile}'

    #stampdata defines marks we want to add to the document and their location
    #emaildata comes from the email profile but can be amended here
    #packitems are the items chosen to be included in the package
    #doclist are the items available to be added to the package
    #dockind is the kind of documents we want for this package
    #stampdata = call_stamp(odat, task_iter)
    fexist, packitems = get_doclist(odat, dockind)

    #print('packitems final:', packitems)
    #print('stampdata final:', stampdata)

    if len(packitems) >= 1:
        pdflist = ['pdfunite'] + packitems + [addpath(docref)]
        tes = subprocess.check_output(pdflist)
    else:
        err.append('No documents available for this selection')

    stampnow = request.values.get('stampnow')
    if stampnow is not None or eprof == 'Paid Invoice':
        #print(f'stamping document going in: {docref}')
        docref = stamp_document(genre, odat, stamplist, stampdata, err, docref)
        #print(f'stamped document coming out: {docref}')

    emaildata[6] = odat.Package
    #print('dockind at end=', dockind)

    try:
        os.remove(oldfile)
    except:
        pass

    return emaildata, stampdata, dockind, docref, err, fexist
