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

def call_stamp(odat, dockind, task_iter, err):
    fexist = [0] * 4
    packitems = []
    pdat = People.query.get(odat.Bid)
    if pdat is None:
        pdat = People.query.filter(People.Company == odat.Shipper).first()
    if pdat is not None:
        stampstring = pdat.Temp2
        try:
            stampdata = json.loads(stampstring)
            if isinstance(stampdata, list):
                print('json loads stampdata is', stampdata)
            else:
                stampdata = None
        except:
            stampdata = None
    else:
        stampdata = None

    print('The stampdata is:', stampdata)
    if stampdata is None:
        stampdata = [3, 35, 35, 5, 120, 100, 5, 477, 350]

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

    print('fexist is',fexist)
    # Get the email data also in case changes occur there
    emaildata = [0] * 7
    for i in range(7):
        emaildata[i] = request.values.get('edat' + str(i))


    print('packitems final:', packitems)
    print('stampdata final:', stampdata)

    return stampdata, emaildata, packitems, fexist



def makepackage(odat, task_iter, document_types, eprof, err):
    err = []
    dockind = ['']*4
    if task_iter > 1 and eprof == 'Custom':
        sections = ['1st Section', '2nd Section', '3rd Section', '4th Section']
        for jx, section in enumerate(sections):
            dockind[jx] = request.values.get(section)
    else:
        dockind = document_types[eprof]
    print('dockind=',dockind)
    try:
        cache2 = int(odat.Pkcache) + 1
    except:
        cache2 = 1
    print('cache2',cache2)
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
    stampdata, emaildata, packitems, fexist = call_stamp(odat, dockind, task_iter, err)

    print('packitems final:', packitems)
    print('stampdata final:', stampdata)
    stampstring = json.dumps(stampdata)
    print(len(stampstring))
    print(stampstring)
    odat.Status = stampstring
    db.session.commit()

    if len(packitems) >= 1:
        pdflist = ['pdfunite'] + packitems + [addpath(docref)]
        tes = subprocess.check_output(pdflist)
    else:
        err.append('No documents available for this selection')

    return stampdata, dockind, docref, err, fexist
