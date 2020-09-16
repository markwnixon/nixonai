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

def call_stamp(odat, doclist):
    doclist = [0] * 8
    packitems = []
    pdat = People.query.get(odat.Bid)
    if pdat is None:
        pdat = People.query.filter(People.Company == odat.Shipper).first()
    if pdat is not None:
        stampstring = pdat.Temp2
        try:
            stampdata = json.loads(stampstring)
            if isinstance(stampdata, list):
                print('stampdata is', stampdata)
            else:
                stampdata = None
        except:
            stampdata = None
    else:
        stampdata = None

    print('The stampdata is:', stampdata)

    if stampdata is not None:

        packitems = []
        doclist = []
        subdata = stampdata[9:13]
        stampdata = stampdata[0:9]

        if len(subdata) == 0:

            doclist[0] = f'tmp/{scac}/data/vorders/{odat.Original}'
            doclist[1] = f'tmp/{scac}/data/vproofs/{odat.Proof}'
            doclist[2] = f'tmp/{scac}/data/vinvoice/{odat.Invoice}'
            doclist[3] = f'tmp/{scac}/data/vinterchange/{odat.Gate}'

            for ix in range(4):
                if dockind[ix] != 'none':
                    fexist[ix] = os.path.isfile(addpath(doclist[ix]))
                    if fexist[ix] == 0:
                        print(f'{addpath(doclist[ix])} does not exist')
                        err.append(f'No {dockind[ix]} Document Exists')
                    else:
                        packitems.append(addpath(doclist[ix]))
                        stampdata.append(dockind[ix])
        else:
            for test in subdata:
                if test != 'none':
                    if test == 'Source':
                        fa = addpath(f'static/{scac}/data/vorders/{odat.Original}')
                        if os.path.isfile(fa):
                            packitems.append(fa)
                            stampdata.append(test)
                    if test == 'Invoice':
                        fa = addpath(f'static/{scac}/data/vinvoice/{odat.Invoice}')
                        if os.path.isfile(fa):
                            packitems.append(fa)
                            stampdata.append(test)
                    if test == 'Proofs':
                        fa = addpath(f'static/{scac}/data/vproofs/{odat.Proof}')
                        if os.path.isfile(fa):
                            packitems.append(fa)
                            stampdata.append(test)
                    if test == 'Ticks':
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
                                stampdata.append(test)
                            else:
                                packitems.append(addpath(f'tmp/{scac}/data/vinterchange/{idata[0].Original}'))
                                stampdata.append(test)

        if len(stampdata) < 13:
            for ix in range(len(stampdata), 13):
                stampdata.append('none')

    # Get the email data also in case changes occur there
    emaildata = [0] * 7
    for i in range(7):
        emaildata[i] = request.values.get('edat' + str(i))


    print('packitems final:', packitems)
    print('stampdata final:', stampdata)

    return stampdata, emaildata, packitems, doclist



def makepackage(odat):
    err = []
    fexist = [0] * 5
    dockind = ['Source', 'Proofs', 'Invoice', 'Gate']
    doclist = [0]*8
    try:
        cache2 = int(odat.Pkcache) + 1
    except:
        cache2 = 1
    basefile = f'P_c{cache2}_{odat.Jo}.pdf'
    odat.Package = basefile
    db.session.commit()
    doclist[7] = f'static/{scac}/data/vpackages/{basefile}'
    docref = doclist[7]

    stampdata, emaildata, packitems, doclist = call_stamp(odat, doclist)
    if stampdata is None:
        stampdata = [3, 35, 35, 5, 120, 100, 5, 477, 350]
        doclist[0] = f'static/{scac}/data/vorders/{odat.Source}'
        doclist[1] = f'static/{scac}/data/vproofs/{odat.Proof}'
        doclist[2] = f'static/{scac}/data/vinvoice/{odat.Invoice}'
        doclist[3] = f'static/{scac}/data/vinterchange/{odat.Gate}'

    for ix in range(4):
        if dockind[ix] != 'none':
            fexist[ix] = os.path.isfile(addpath(doclist[ix]))
            if fexist[ix] == 0:
                print(f'{addpath(doclist[ix])} does not exist')
                err.append(f'No {dockind[ix]} Document Exists')
            else:
                packitems.append(addpath(doclist[ix]))
                stampdata.append(dockind[ix])

    if len(stampdata) < 13:
        for ix in range(len(stampdata), 13):
            stampdata.append('none')

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
        doclist[0] = docref
    else:
        err.append('No documents available for this selection')
        viewtype, mpack, stamp, leftscreen = 0, 0, 0, 1

    return stampdata, docref
