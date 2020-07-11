from webapp import db
from webapp.models import Vehicles, Invoices, Orders, Bills, Accounts, People, Interchange, Drivers, Drops, Chassis, Services, Trucklog
from datetime import datetime, timedelta
import os
import shutil
import subprocess
from webapp.CCC_system_setup import addpath, scac, companydata
from webapp.viewfuncs import d2s
from webapp.iso_Bank import banktotals

from fpdf import FPDF
from PIL import Image

def check_for_vin(msg):
    vlist = msg.splitlines()
    vtest = 1
    for v in vlist:
        if len(v) < 17 or len(v) > 18:
            vtest = 0
    return vtest, vlist


def save_Original(jo, imagelist):

    outfile = ''
    pdf = FPDF()
    # imagelist is the list with all image filenames
    for image in imagelist:
        iname = image.lower()
        filename = addpath(f'tmp/{scac}/data/processing/whatsapp/')+image
        outfile = jo + '.pdf'
        if 'pdf' in iname:
            shutil.move(filename, addpath(f'tmp/{scac}/data/vorders/'+outfile))
        elif 'jpg' or 'png' in iname:
            if 'jpg' in iname:
                ext = 'jpeg'
            elif 'png' in iname:
                ext = 'png'
            im = Image.open(filename)
            width, height = im.size
            if width > 600:
                w = 600
                h = int(height*(600.0/float(width)))
                new_img = im.resize((w, h))
                new_img.save(filename, ext, optimize=True)
            else:
                w = width
                h = height
            print('w,h = ', width, height, w, h)
            pdf.add_page()
            pdf.image(filename, 0, 0)
            pdf.output(addpath(f'tmp/{scac}/data/vorders/'+outfile), "F")
            os.remove(filename)
    return outfile


def getjo(sessionph):

    fileph = sessionph[-7:]
    try:
        fname = f'tmp/{scac}/data/processing/seq_{fileph}.txt'
        file1 = open(addpath(fname))
        text = file1.readline()
        text = text.split()
        seq = text[0]
        jo = text[1]
        file1.close()
    except IOError:
        jo = '0'
        seq = '0'
    except IndexError:
        print('Encountered indexing error')
    return seq, jo


def putjo(seq, jo, sessionph):

    fileph = sessionph[-7:]
    fname = f'tmp/{scac}/data/processing/seq_{fileph}.txt'
    print(fileph,fname)
    file1 = open(addpath(fname), 'w+')
    file1.write(seq+' '+jo)
    file1.close()


def appendline(list, sessionph):

    fileph = sessionph[-7:]
    fname = f'tmp/{scac}/data/processing/seq_{fileph}.txt'
    file1 = open(addpath(fname), 'a')
    for item in list:
        file1.write('\n'+item)
    file1.close()


def gettext(sessionph):

    fileph = sessionph[-7:]
    fname = f'tmp/{scac}/data/processing/seq_{fileph}.txt'
    file1 = open(addpath(fname))
    text = file1.readlines()
    file1.close()
    return text


def test_neg_response(c):

    ll = len(c)
    if ll == 1 and (c == 'n' or c == 'q'):
        return 1
    elif ll == 2 and (c == 'no' or c == 'qu'):
        return 1
    elif ll == 4 and c == 'quit':
        return 1
    else:
        return 0


def end_sequence(sessionph):
    try:
        fileph = sessionph[-7:]
        fname = f'tmp/{scac}/data/processing/seq_{fileph}.txt'
        os.remove(addpath(fname))
    except IOError:
        print('File already removed')


def test_session_quit(c, sessionph):
    ll = len(c)
    if ll == 4 and c == 'quit':
        try:
            fileph = sessionph[-7:]
            fname = f'tmp/{scac}/data/processing/seq_{fileph}.txt'
            os.remove(addpath(fname))
        except IOError:
            print('File already removed')

def get_out_msg():
    cdata = Interchange.query.filter( (Interchange.Status != 'IO') & (Interchange.Type.contains('Out') ) ).all()
    newmsg = '*ContainerS OUT*'
    for cdat in cdata:
        sdate = cdat.Date
        sdate = sdate.strftime('%m/%d')
        newmsg = newmsg + f'\n{cdat.Container} on {sdate}'

    cdata = Chassis.query.filter(Chassis.Datein == 'Still Out').all()
    newmsg =  newmsg + '\n\n*DCLI Chassis OUT*'
    for cdat in cdata:
        sdate = cdat.Dateout
        sdate = sdate[0:5]
        newmsg = newmsg + f'\n{cdat.Chass} on {sdate}'
        newmsg = newmsg + f'\nwith {cdat.Container}'
    return (newmsg)

def get_new_customer(compare,sequence,sessionph):
    if sequence[1]=='0':
        newmsg = 'OK, what is name of customer?'
        sequence = sequence.replace('C0', 'C1')
        putjo(sequence, 'Customer', sessionph)
        return newmsg


    elif sequence[1]=='1':
        # This is start of sequence to enter a new customer
        today = datetime.today()
        today = today.date()
        customer = compare.title()

        ptest = People.query.filter(People.Company == customer).first()

        if ptest is None:

            input = People(Company=customer, First=None, Middle=None, Last=None, Addr1=None, Addr2=None, Addr3=None,
                               Idtype=None, Idnumber=None, Telephone=None,
                               Email=None, Associate1=None, Associate2=None, Date1=today, Date2=None, Original=None,
                               Ptype='Trucking', Temp1=None, Temp2=None, Accountid=None)
            db.session.add(input)
            db.session.commit()
            pdat = People.query.filter(People.Company == customer).first()
            pid = pdat.id
            sequence = sequence.replace('C1', 'C2')
            putjo(sequence, 'Customer', sessionph)
            appendline([customer, str(pid)], sessionph)
            newmsg = f'Customer Added:\n*{customer}*'
            newmsg = newmsg + '\n\nEnter customer details:\n<street address>\n<city-state-zip>\n<phone>\n<email>'
            newmsg = newmsg + '\n\nor NO to opt out\n\nOne item per line\nLeave blank as needed.'
        else:
            newmsg = f'Customer *{customer}* already exists\nTry again....\n'
        return newmsg

    elif sequence[1] == '2':
        # Get the current info from text file:
        text = gettext(sessionph)
        customer = text[1].strip()
        pid = text[2]
        pid = int(pid)
        # No matter what the response we will move on from here so write out the txt file to move on
        sequence = sequence.replace('C2', 'C3')
        putjo(sequence, 'Customer', sessionph)
        appendline([customer, str(pid)], sessionph)
        kickout = test_neg_response(compare)

        if kickout == 1:
            # Time to move on, will put the details of customer in later
            newmsg = 'Moving On....'
        else:
            pdat = People.query.get(pid)
            customer = pdat.Company
            clines = compare.splitlines()
            newmsg = f'New Customer Entered:\n\n{customer}'
            for j, line in enumerate(clines):
                line = line.title()
                if j == 0:
                    pdat.Addr1 = line
                    newmsg = newmsg + '\nAddr1: ' + line
                if j == 1:
                    pdat.Addr2 = line
                    newmsg = newmsg + '\nAddr2: ' + line
                if j == 2:
                    pdat.Telephone = line
                    newmsg = newmsg + '\nPhone: ' + line
                if j == 3:
                    pdat.Email = line
                    newmsg = newmsg + '\nEmail: ' + line
                db.session.commit()

            newmsg = newmsg + f'\n\nCut, Paste into Next Block and Modify Info to Adjust...'
            end_sequence(sessionph)
        return newmsg

def get_new_drop(compare,sequence,sessionph):
    if sequence[1]=='0':
        newmsg = f'Enter Drop Details:\n\n'
        newmsg = newmsg + '<drop name>\n<street address>\n<city-state-zip>\n<phone>\n<email>'
        newmsg = newmsg + '\n\nor NO to opt out\n\nOne item per line\nLeave blank as needed.'
        sequence = sequence.replace('D0', 'D1')
        putjo(sequence, 'Drop', sessionph)
        return newmsg

    elif sequence[1]=='1':
        # This is start of sequence to enter a new drop location
        getlines = compare.splitlines()
        try:
            location = getlines[0].strip()
        except:
            location = 'None'
        try:
            addr1 = getlines[1].strip()
        except:
            addr1 = ''
        try:
            addr2 = getlines[2].strip()
        except:
            addr2 = ''
        try:
            phone = getlines[3].strip()
        except:
            phone = ''
        try:
            email = getlines[4].strip()
        except:
            email = ''

        ptest = Drops.query.filter(Drops.Entity == location).first()

        if ptest is None:

            input = Drops(Entity=location, Addr1 = addr1, Addr2 = addr2, Phone = phone, Email = email)
            db.session.add(input)
            db.session.commit()

            newmsg = f'New Drop Location Added:\n{location}'
            newmsg = newmsg + f'\nAddr1: {addr1}\nAddr2: {addr2}\nPhone: {phone}\nEmail: {email}'
            newmsg = newmsg + f'\n\nCut, Paste into Next Block and Modify Info to Adjust...'

            end_sequence(sessionph)

        else:
            newmsg = f'Drop Location *{location}* already exists\nTry again....\n'

        return newmsg


def get_superkey(msg):
    try:
        allines = msg.splitlines()
        superkey = allines[0]
        superkey = superkey.strip()
    except:
        superkey = 'NoKey'
    return superkey

def mod_for_superkey(keyitem,msg):

    if keyitem == 'drops':
        all = msg.splitlines()
        location = all[1].strip()
        addr1 = all[2].replace('Addr1:','').strip()
        addr2 = all[3].replace('Addr2:','').strip()
        phone = all[4].replace('Phone:','').strip()
        email = all[5].replace('Email:','').strip()
        ddat = Drops.query.filter(Drops.Entity == location).first()
        if ddat is not None:
            ddat.Addr1 = addr1
            ddat.Addr2 = addr2
            ddat.Phone = phone
            ddat.Email = email
            db.session.commit()
        elif len(location) > 3:
            input = Drops(Entity=location, Addr1 = addr1, Addr2 = addr2, Phone = phone, Email = email)
            db.session.add(input)
            db.session.commit()


        newmsg = f'Drop Location Modified:\n{location}'
        newmsg = newmsg + f'\nAddr1: {addr1}\nAddr2: {addr2}\nPhone: {phone}\nEmail: {email}'
        newmsg = newmsg + f'\n\nCut, Paste into Next Block and Modify Info to Adjust...'

        return newmsg

    if keyitem == 'customer':
        today = datetime.today()
        today = today.date()
        all = msg.splitlines()
        try:
            customer = all[2].strip()
        except:
            customer = ''
        try:
            addr1 = all[3].replace('Addr1:','').strip()
        except:
            addr1 = ''
        try:
            addr2 = all[4].replace('Addr2:','').strip()
        except:
            addr2 = ''
        try:
            phone = all[5].replace('Phone:','').strip()
        except:
            phone = ''
        try:
            email = all[6].replace('Email:','').strip()
        except:
            email = ''
        print(f'Entering customer:{customer},addr1:{addr1} addr2:{addr2} Phone:{phone} Email:{email}')
        cdat = People.query.filter(People.Company == customer).first()
        if cdat is not None:
            cdat.Addr1 = addr1
            cdat.Addr2 = addr2
            cdat.Telephone = phone
            cdat.Email = email
            db.session.commit()
        elif len(customer) > 3:
            input = People(Company=customer, First=None, Middle=None, Last=None, Addr1=addr1, Addr2=addr2, Addr3=None,
                           Idtype=None, Idnumber=None, Telephone=phone,
                           Email=email, Associate1=None, Associate2=None, Date1=today, Date2=None, Original=None,
                           Ptype='Trucking', Temp1=None, Temp2=None, Accountid=None)
            db.session.add(input)
            db.session.commit()


        newmsg = f'New Customer Modified:\n{customer}'
        newmsg = newmsg + f'\nAddr1: {addr1}\nAddr2: {addr2}\nPhone: {phone}\nEmail: {email}'
        newmsg = newmsg + f'\n\nCut, Paste into Next Block and Modify Info to Adjust...'

        return newmsg

def get_manifest(msg,sequence,sessionph,jo):
   pdffile = ''
   if sequence[1] == '0':
       # Get list of Uncompleted Orders...
       newmsg = '*Uncompleted Jobs*\n'
       odata = Orders.query.filter( (Orders.Status.startswith('A')) | (Orders.Status.startswith('1')) ).all()
       for odat in odata:
           shipper = odat.Shipper
           company = odat.Company
           company2 = odat.Company2
           jo = odat.Jo
           oid = odat.id
           if shipper is None:
               shipper = 'NAY'
           if company is None:
               company = 'NAY'
           if company2 is None:
               company2 = 'NAY'
           if len(shipper) > 12:
               shipper = shipper[0:12]
           if len(company) > 8:
               company = company[0:8]
           if len(company2) > 8:
               company2 = company2[0:8]
           newmsg = newmsg + f'\n*{oid}* for {shipper}\nD1:{company}  D2:{company2}\n'

       newmsg = newmsg + '\nEnter bold number'
       sequence = sequence.replace('M0', 'M1')
       putjo(sequence, 'Manifest', sessionph)
       if len(odata)<1:
           newmsg = 'No Uncompleted Jobs'

       return newmsg

   elif sequence[1] =='1':
       mid = msg.lower().strip()
       oid = int(mid)
       newmsg = ''
       odat = Orders.query.get(oid)
       if odat is not None:
           newmsg = f'Selected _{mid}_ JO:_{odat.Jo}_\n\n'

       newmsg = newmsg + f'*Select Driver:*\n'
       ddata = Drivers.query.all()
       for ddat in ddata:
           driver = ddat.Name
           d3 = ddat.id
           newmsg = newmsg + f'*{d3}* {driver}\n'

       sequence = sequence.replace('M1', 'M2')
       putjo(sequence, jo, sessionph)
       appendline([mid], sessionph)
       return newmsg

   elif sequence[1] =='2':
       drv = msg.lower().strip()
       rid = int(drv)
       newmsg = ''
       ddat = Drivers.query.get(rid)
       if ddat is not None:
           driver = ddat.Name
           newmsg = f'Selected _{driver}_\n\n'

       text = gettext(sessionph)
       mid = text[1].strip()

       sequence = sequence.replace('M2', 'M3')
       putjo(sequence, jo, sessionph)
       appendline([mid,drv], sessionph)

       newmsg = newmsg + f'*Select Truck:*\n'
       ddata = Vehicles.query.all()
       for ddat in ddata:
           truck = ddat.Plate
           d3 = ddat.id
           newmsg = newmsg + f'*{d3}* {truck}\n'
       return newmsg

   elif sequence[1] =='3':
       trk = msg.lower().strip()
       tid = int(trk)
       newmsg = ''
       tdat = Vehicles.query.get(tid)
       if tdat is not None:
           plate = tdat.Plate
           newmsg = newmsg + f'Selected _{plate}_\n\n'

       text = gettext(sessionph)
       mid = text[1].strip()
       drv = text[2].strip()

       sequence = sequence.replace('M3', 'M4')
       putjo(sequence, jo, sessionph)
       appendline([mid,drv,trk], sessionph)

       newmsg = newmsg + f'*Enter Commodity:*\nCheese, Office, Furniture, Sugar, Tires...etc'
       return newmsg

   elif sequence[1] =='4':
       com = msg.title().strip()
       newmsg = f'Entered: _{com}_\n\n'

       text = gettext(sessionph)
       mid = text[1].strip()
       drv = text[2].strip()
       trk = text[3].strip()

       sequence = sequence.replace('M4', 'M5')
       putjo(sequence, jo, sessionph)
       appendline([mid,drv,trk,com], sessionph)

       newmsg = newmsg + f'*Enter Packing:*\n18 Pallets, Each, ...etc'
       return newmsg

   elif sequence[1] == '5':
       pak = msg.title().strip()
       newmsg = f'Entered: _{pak}_\n\n'

       text = gettext(sessionph)
       mid = text[1].strip()
       drv = text[2].strip()
       trk = text[3].strip()
       com = text[4].strip()

       sequence = sequence.replace('M5', 'M6')
       putjo(sequence, jo, sessionph)
       appendline([mid,drv,trk,com,pak], sessionph)

       newmsg = newmsg + f'*Time In:*'
       return newmsg

   elif sequence[1] == '6':
       tm1 = msg.lower().strip()
       newmsg = f'Entered: _{tm1}_\n\n'

       text = gettext(sessionph)
       mid = text[1].strip()
       drv = text[2].strip()
       trk = text[3].strip()
       com = text[4].strip()
       pak = text[5].strip()

       sequence = sequence.replace('M6', 'M7')
       putjo(sequence, jo, sessionph)
       appendline([mid,drv,trk,com,pak,tm1], sessionph)

       newmsg = newmsg + f'*Time Out*'
       return newmsg

   elif sequence[1] == '7':

       tm2 = msg.lower().strip()

       text = gettext(sessionph)
       mid = text[1].strip()
       drv = text[2].strip()
       trk = text[3].strip()
       com = text[4].strip()
       pak = text[5].strip()
       tm1 = text[6].strip()

       newmsg = 'File Attachment\n'

       from makemanifest2 import makemanifestT
       oid = int(mid)
       drv = int(drv)
       trk = int(trk)
       odat = Orders.query.get(oid)
       cache = int(odat.Detention)
       jo = odat.Jo
       bol = odat.BOL
       if bol is None:
           bol = ' '
       p1 = odat.Bid
       p2 = odat.Lid
       p3 = odat.Did
       pdat1 = People.query.get(p1)
       pdat2 = Drops.query.get(p2)
       pdat3 = Drops.query.get(p3)
       jtype = 'Trucking'
       tdat = Vehicles.query.get(trk)
       drvdat = Drivers.query.get(drv)

       docref = makemanifestT(odat, pdat1, pdat2, pdat3, tdat, drvdat, cache, jtype, tm1, tm2, com, pak, bol)

       basename = 'Man_' + jo + '.pdf'
       shutil.copy(addpath(docref), addpath(f'tmp/{scac}/data/' + basename))
       newmsg = newmsg + f'tmp/{scac}/data/{basename}'
       newmsg = newmsg + '\n\nAmend depart time or *Quit* sequence'

       return newmsg

def add_invo(oid,text):
    today = datetime.today()
    ltext = len(text)
    odat = Orders.query.get(oid)
    jo = odat.Jo
    company = odat.Shipper
    oid = odat.id
    bid = odat.Bid
    try:
        total = float(odat.Amount)
    except:
        total = 0.00
    descript = ''
    input = Invoices(Jo=jo, SubJo=None, Pid=bid, Service='Line Haul', Description=None,
                     Ea=odat.Amount, Qty=1, Amount=total, Total=total, Date=today, Original=None, Status='Quote')
    db.session.add(input)
    db.session.commit()

    for lt in text[2:]:
        lt = lt.strip()
        ltl = lt.split()
        sid = int(ltl[0])
        sdat = Services.query.get(sid)
        service = sdat.Service
        qty = float(ltl[1])
        each = float(sdat.Price)
        total = qty*each
        input = Invoices(Jo=jo, SubJo=None, Pid=bid, Service=service, Description=None,
                         Ea=each, Qty=qty, Amount=total, Total=total, Date=today, Original=None, Status='Quote')
        db.session.add(input)
        db.session.commit()

def get_invoice(msg,sequence,sessionph):

    today = datetime.today()
    pdffile = ''
    if sequence[1] == '0':
       sequence = sequence.replace('I0', 'I1')
       putjo(sequence, 'Invoice', sessionph)
       # Get list of open invoices...
       newmsg = '*Unpaid Jobs*\n'
       odata = Orders.query.filter(Orders.Status != '33').all()
       for odat in odata:
           pid = int(odat.Bid)
           cdat = People.query.get(pid)
           if cdat is not None:
               jo = odat.Jo
               jid = odat.id
               company = cdat.Company
               total = str(odat.Amount)
               if len(company) > 12:
                   company = company[0:12]
               newmsg = newmsg + f'*{jid}* {company} ${total}\n'
       newmsg = newmsg + '\nEnter bold number'
       return newmsg

    if sequence[1] == '1':
       text = gettext(sessionph)
       mid = int(msg.lower().strip())
       odat = Orders.query.get(mid)
       jo = odat.Jo
       bid = odat.Bid
       company = odat.Shipper
       oid = odat.id
       if len(company) > 12:
           company = company[0:12]
       amount = odat.Amount
       newmsg = f'Creating Invoice for {company}'
       newmsg = newmsg + f'\nLine Haul: {amount}'
       newmsg = newmsg + '\n\nEnter the Following Quantities, seperated by space.\nEnter 0 if None or not Applicable.\n<Line Haul Amt> <Chassis Days> <Driver Detention Hrs> <Days Storage>'

       sequence = sequence.replace('I1', 'I2')
       putjo(sequence, 'Invoice', sessionph)
       appendline([str(mid)], sessionph)

       return newmsg

    if sequence[1] == '2':

       text = gettext(sessionph)
       ltext = len(text)
       mid = int(text[1].strip())

       odat = Orders.query.get(mid)
       jo = odat.Jo
       bid = odat.Bid
       company = odat.Shipper

       qtyline = msg.split()
       try:
           lineamt = float(qtyline[0])
       except:
           lineamt = 0.00
       try:
           days = float(qtyline[1])
       except:
           days = 0
       try:
           det = float(qtyline[2])
       except:
           det = 0
       try:
           sto = float(qtyline[3])
       except:
           sto = 0

       tot = 0.00
       ldat = Invoices.query.filter( (Invoices.Jo == jo) & (Invoices.Service == 'Line Haul') ).first()
       if ldat is not None:
           ldat.Amount = lineamt
       else:
           input = Invoices(Jo=jo, SubJo=None, Pid=bid, Service='Line Haul', Description=None,
                            Ea=lineamt, Qty=1, Amount=lineamt, Total=0.00, Date=today, Original=None, Status='New')
           db.session.add(input)
       db.session.commit()

       qtys = [days, det, sto]

       for j, ser in enumerate(['Chassis', 'Detention', 'Storage']):
           sdat = Services.query.filter(Services.Service.contains(ser)).first()
           if sdat is not None:
               service = sdat.Service
               ech = float(sdat.Price)
               num = qtys[j]
               amt = ech*num
               ldat = Invoices.query.filter((Invoices.Jo == jo) & (Invoices.Service == service)).first()
               if ldat is not None and num < 1.0:
                   lid = ldat.id
                   Invoices.query.filter(Invoices.id == lid).delete()
                   db.session.commit()
               else:
                   if ldat is not None and num > 0.0:
                       ldat.Ea = ech
                       ldat.Qty = num
                       ldat.Amount = amt
                       db.session.commit()
                   elif num > 0.0:
                       input = Invoices(Jo=jo, SubJo=None, Pid=bid, Service=service, Description=None,
                                        Ea=ech, Qty=num, Amount=amt, Total=0.00, Date=today, Original=None, Status='New')
                       db.session.add(input)
                       db.session.commit()

       ldata = Invoices.query.filter(Invoices.Jo == jo).all()
       for ldat in ldata:
           amt = float(ldat.Amount)
           tot = tot + amt
       for ldat in ldata:
           ldat.Total = tot
           db.session.commit()

       newmsg = 'File Attachment\n'

       cache = int(odat.Detention)
       p1 = odat.Bid
       p2 = odat.Lid
       p3 = odat.Did
       pdat1 = People.query.get(p1)
       if p2 is not None:
           pdat2 = Drops.query.get(p2)
       else:
           pdat2 = None
       if p3 is not None:
           pdat3 = Drops.query.get(p3)
       else:
           pdat3 = None

       from make_T_invoice import T_invoice
       docref = T_invoice(odat, ldata, pdat1, pdat2, pdat3, cache, today, 0)

       basename = 'Inv_' + jo + '.pdf'
       shutil.copy(docref, addpath(f'tmp/{scac}/data/' + basename))
       newmsg = newmsg + f'tmp/{scac}/data/{basename}'

       return newmsg

    else:
       putjo(sequence, 'Invoice', sessionph)
       for textline in text[1:]:
           appendline([textline.strip()], sessionph)

    return newmsg



def get_bank_info(compare, sequence, sessionph):

    try:
        if sequence[1] == '0':
            newmsg = '_Bank Data Requested_\n*Choose Bank:*\n'
            adata = Accounts.query.filter(Accounts.Type == 'Bank').all()
            for adat in adata:
                bk = adat.Name
                sh = adat.id
                newmsg = newmsg + f'*{str(sh)}*: {bk}\n'
            newmsg = newmsg + '_Enter bold number_'
            sequence = sequence.replace('B0', 'B1')
            putjo(sequence, 'Bank', sessionph)
          
        elif sequence[1] == '1':
            # Select the bank from the msg:
            id = int(compare)
            adat = Accounts.query.get(id)
            name = adat.Name
            acctinfo = banktotals(name)
            newmsg = f'*{acctinfo[6]}*\nCurrent Balance: *${acctinfo[0]}*\n   Total Deposited: ${acctinfo[7]}\n   Total Withdrawn: ${acctinfo[8]}'
            end_sequence(sessionph)
            
    except:
        newmsg = 'Entered Bank Area No Return'

    return newmsg

def get_quote(msg,sequence,sessionph):

    today = datetime.today()
    if sequence[1] == '0':
        sequence = sequence.replace('Q0', 'Q1')
        putjo(sequence, 'Quote', sessionph)
        # Get list of open invoices...
        newmsg = '*Jobs Without Quotes*\n'
        odata = Orders.query.filter((Orders.Status == '00') | (Orders.Status == 'A0')).all()
        for odat in odata:
           company = odat.Shipper
           oid = odat.id
           if len(company) > 12:
               company = company[0:12]
           newmsg = newmsg + f'*{oid}* {company}\n'
        newmsg = newmsg + '\nEnter bold number'

        return newmsg

    if sequence[1] == '1':
        text = gettext(sessionph)
        mid = int(msg.lower().strip())
        odat = Orders.query.get(mid)
        jo = odat.Jo
        company = odat.Shipper
        oid = odat.id
        if len(company) > 12:
           company = company[0:12]
        amount = odat.Amount
        newmsg = f'Creating Quote for {company}'
        newmsg = newmsg + f'\nLine Haul: {amount}'
        newmsg = newmsg + '\n\nJob Will Start in About How Many Days?'

        sequence = sequence.replace('Q1', 'Q2')
        putjo(sequence, 'Quote', sessionph)
        appendline([str(mid)], sessionph)

        return newmsg

    if sequence[1] == '2':

        days = int(msg.lower().strip())
        text = gettext(sessionph)
        ltext = len(text)
        mid = int(text[1].strip())

        odat = Orders.query.get(mid)
        start = today + timedelta(days)
        finish = today + timedelta(days+2)
        start = start.date()
        finish = finish.date()
        odat.Date = start
        odat.Date2 = finish
        db.session.commit()

        sequence = sequence.replace('Q2', 'Q3')
        putjo(sequence, 'Quote', sessionph)
        appendline([str(mid)], sessionph)

        jo = odat.Jo
        company = odat.Shipper
        oid = odat.id
        if len(company) > 12:
           company = company[0:12]
        amount = odat.Amount
        newmsg = f'Creating Quote for {company}'
        newmsg = newmsg + f'\nLine Haul: {amount}'

        newmsg = newmsg + f'\n\nEnter Code for Next Item to Include\nFollow Code with Qty:'
        sdata = Services.query.all()
        for sdat in sdata:
           newmsg = newmsg + f'\n*{str(sdat.id)}* {sdat.Service} {d2s(sdat.Price)}'

        return newmsg

    if sequence[1] == '3':

        newserviceline = msg.lower().strip()

        text = gettext(sessionph)
        if 'g' not in newserviceline:
            text.append(newserviceline)
        ltext = len(text)
        mid = int(text[1].strip())

        odat = Orders.query.get(mid)
        jo = odat.Jo
        company = odat.Shipper
        oid = odat.id
        if len(company) > 12:
           company = company[0:12]
        amount = odat.Amount
        newmsg = f'Creating Quote for {company}'
        newmsg = newmsg + f'\nLine Haul: {amount}'

        if ltext > 1:
           print('ltext =',ltext)
           tot = 0.0
           for lt in text[2:]:
               lt = lt.strip()
               ltl=lt.split()
               sid = int(ltl[0])
               sdat = Services.query.get(sid)
               service = sdat.Service
               qty = ltl[1]
               ech = float(sdat.Price)
               num = float(qty)
               amt = ech*num
               tot = tot + amt

               #Make day estimate consistent with job
               if 'chassis' in service.lower():
                   start = odat.Date
                   jobdays = int(qty) - 1
                   finish = start + timedelta(jobdays)
                   odat.Date2 = finish
                   db.session.commit()

               newmsg = newmsg + f'\n{qty} {service} x {d2s(ech)} Ea = {d2s(amt)}'
        newmsg = newmsg + '\n\n*G* Get Quote of Above or...'
        newmsg = newmsg + f'\n\nEnter Code for Next Item to Include\n(Follow Code with Space then Qty #):'
        sdata = Services.query.all()
        for sdat in sdata:
           newmsg = newmsg + f'\n*{str(sdat.id)}* {sdat.Service} {d2s(sdat.Price)}'

        if 'g' in newserviceline:
           sequence = sequence.replace('Q3', 'Q4')
           #Put all the data in the invoice
           #First delete any previous quotes:
           Invoices.query.filter( (Invoices.Jo == jo) & (Invoices.Status == 'Quote')).delete()
           add_invo(oid,text)
           ldata = Invoices.query.filter(Invoices.Jo == jo).all()

           newmsg = 'File Attachment\n'

           cache = int(odat.Detention)
           p1 = odat.Bid
           p2 = odat.Lid
           p3 = odat.Did
           pdat1 = People.query.get(p1)
           if p2 is not None:
               pdat2 = Drops.query.get(p2)
           else:
               pdat2 = None
           if p3 is not None:
               pdat3 = Drops.query.get(p3)
           else:
               pdat3 = None

           from make_T_quote import T_quote
           docref = T_quote(odat, ldata, pdat1, pdat2, pdat3, cache, today)

           basename = 'Quo_' + jo + '.pdf'
           shutil.copy(docref, addpath(f'tmp/{scac}/data/' + basename))
           newmsg = newmsg + f'tmp/{scac}/data/{basename}'

           return newmsg

        else:
            putjo(sequence, 'Quote', sessionph)
            for textline in text[1:]:
                appendline([textline.strip()], sessionph)



        return newmsg


def make_global_job(msg,sequence,sessionph):
    from viewfuncs import parseline, popjo, jovec, newjo, timedata, nonone, nononef, init_truck_zero, dropupdate
    today = datetime.today()
    sdate = today.strftime('%Y-%m-%d')

    if sequence[1] == '0':
        sequence = sequence.replace('G0', 'G1')
        putjo(sequence, 'Global', sessionph)
        # Create job for each booking...get booking
        newmsg = '*Enter one or more Bookings for Global Jobs*\n'
        return newmsg

    if sequence[1] == '1':
        newmsg = 'Adding Global Jobs:\n'
        text = gettext(sessionph)
        bookings = msg.split()
        pdat1 = People.query.filter(People.Company == 'Global Business Link').first()
        ddat = Drops.query.filter(Drops.Entity == 'Global Business Link').first()
        if ddat is not None:
            drop1 = ddat.Entity + '\n' + ddat.Addr1 + '\n' + ddat.Addr2 + '\n' + ddat.Phone + '\n' + ddat.Email
            company = ddat.Entity
            lid = ddat.id
        else:
            drop1 = None
            company = None
            lid = None
        ddat = Drops.query.filter(Drops.Entity == 'Baltimore Seagirt').first()
        if ddat is not None:
            drop2 = ddat.Entity + '\n' + ddat.Addr1 + '\n' + ddat.Addr2 + '\n' + ddat.Phone + '\n' + ddat.Email
            company2 = ddat.Entity
            did = ddat.id
        else:
            drop2 = None
            company2 = None
            did = None

        for book in bookings:
            book = book.strip()
            odat = Orders.query.filter(Orders.Booking == book).first()
            if odat is None:
                cdata = companydata()
                jbcode = cdata[10] + 'T'
                nextjo = newjo(jbcode, sdate)

                input = Orders(Status='A0', Jo=nextjo, Load=None, Order=nextjo, Company=company, Location=None, Booking=book,
                               BOL=None, Container='TBD',Date=today, Driver=sessionph, Company2=company2, Time=None, Date2=today, Time2=None, Seal=None,
                               Pickup=None, Delivery=None,Amount='275.00', Path=None, Original=None, Description=None, Chassis=None, Detention='0',
                               Storage='0',Release=0, Shipper=pdat1.Company, Type=None, Time3=None, Bid=pdat1.id, Lid=lid, Did=did,
                               Label=None, Dropblock1=drop1, Dropblock2=drop2, Commodity=None, Packing=None,
                               Links=None, Hstat=-1,Istat=-1, Proof=None, Invoice=None, Gate=None, Package=None,
                               Manifest=None,Scache=0,Pcache=0,Icache=0,Mcache=0,Pkcache=0, QBi=0, InvoTotal='275.00')
                db.session.add(input)
                db.session.commit()

                newmsg = f'*{book}* added with JO: *{nextjo}*\n'
            else:
                newmsg = f'*{book}* already in system with JO: {odat.Jo}\n'

        return newmsg




def msg_analysis(msg, sessionph, medialist):

    from viewfuncs import parseline, popjo, jovec, newjo, timedata, nonone, nononef, init_truck_zero, dropupdate

    today = datetime.today()
    today = today.date()
    sdate = today.strftime('%Y-%m-%d')
    compare = msg.lower()
    print('sessionph = ', sessionph)
    
    # Superkey looks for modification scenarios on certain events
    superkey = get_superkey(msg)
    print('my superkey is',superkey)
    if superkey == 'New Drop Location Added:' or superkey == 'Drop Location Modified':
        end_sequence(sessionph)
        newmsg = mod_for_superkey('drops',msg)
        return newmsg
    if superkey == 'New Customer Entered:' or superkey == 'New Customer Modified:':
        end_sequence(sessionph)
        newmsg = mod_for_superkey('customer',msg)
        return newmsg

    # See if session wants to opt out now
    test_session_quit(compare, sessionph)


    sequence, jo = getjo(sessionph)
    newjob = 0
    vintest, vinlist = check_for_vin(msg)
    print('vintest',vintest,vinlist)


    print('sequence at top is ', sequence)

    # Check to start a sequence from provided menu items, else a sequence is in progress
    if sequence == '0':

        if len(compare) == 2 and compare in ['t1', 't2', 't3','t4', 't5', 't6', 't7', 'tn']:
            num = compare[1]
            compare = 'trk' + num
            print('comaprehere',compare)
        try:
            compare = compare[0:3]
        except:
            newmsg = 'Do not recognize the request'
            
        if 'job' in compare:
            newjob = 1
        if 'glo' in compare:
            sequence = 'G0'
            newmsg = make_global_job(compare, sequence, sessionph)
            return newmsg
        if 'out' in compare:
            newmsg = get_out_msg()
            return newmsg
        if 'bal' in compare:
            sequence = 'B0'
        if 'cus' in compare:
            sequence = 'C0'
            newmsg = get_new_customer(compare, sequence, sessionph)
            return newmsg
        if 'drp' in compare or 'dro' in compare:
            sequence = 'D0'
            newmsg = get_new_drop(msg,sequence,sessionph)
            return newmsg
        if 'inv' in compare:
            sequence = 'I0'
            newmsg = get_invoice(msg,sequence,sessionph)
            return newmsg
        if 'man' in compare:
            sequence = 'M0'
            newmsg = get_manifest(msg, sequence, sessionph, jo)
            return newmsg
        if 'quo' in compare:
            sequence = 'Q0'
            newmsg = get_quote(msg, sequence, sessionph)
            return newmsg
        if 'trk' in compare:
            phone = sessionph.replace('whatsapp:+1','')
            ddat = Drivers.query.filter(Drivers.Phone == phone).first()
            if ddat is not None:
                driver = ddat.Name
            else:
                driver = 'NAY'
            print('Driver is',driver)
            tid = msg.lower().replace('t','')
            try:
                tid = int(tid)
                tdat = Vehicles.query.get(tid)
                tag = tdat.Plate
                ldat = Trucklog.query.filter((Trucklog.Date == today) & (Trucklog.Tag == tag)).first()

                if ldat is not None:
                    ldat.Driver = driver
                    ldat.Phone = sessionph
                else:
                    input = Trucklog(Date=today, GPSin=None, GPSout=None, Tag=tag, Distance=None,
                                     Stoptime=None, Gotime=None, Odomstart=None, Odomstop=None, Odverify=None,
                                     Driver=driver, Phone=sessionph, Maintrecord=None, Locationstart=None, Locationstop=None,
                                     Maintid=None, Status='0')
                    db.session.add(input)
                    db.session.commit()

                newmsg = f'Driver {driver} driving with {tag} on {sdate}'

            except:
                newmsg = f'Driver {driver} is not assigned'

            return newmsg

    print('Entering main sequence:',sequence,vintest,vinlist)

    if sequence[0] =='C':
        newmsg = get_new_customer(compare, sequence, sessionph)
        return (newmsg)
    if sequence[0] =='D':
        newmsg = get_new_drop(msg, sequence, sessionph)
        return (newmsg)
    if sequence[0] =='I':
        newmsg = get_invoice(compare, sequence, sessionph)
        return newmsg
    if sequence[0] =='Q':
        newmsg = get_quote(compare, sequence, sessionph)
        return newmsg
    if sequence[0] =='M':
        newmsg = get_manifest(msg, sequence, sessionph, jo)
        return newmsg
    if sequence[0] == 'B':
        newmsg = get_bank_info(compare, sequence, sessionph)
        return newmsg
    if sequence[0] == 'G':
        newmsg = make_global_job(compare, sequence, sessionph)
        return newmsg
        

    if newjob == 1 or sequence[0] == 'J':
        if newjob == 1:
            sequence = 'J0000000000'
            cdata = companydata()
            jbcode = cdata[10] + 'T'
            nextjo = newjo(jbcode, sdate)
            putjo(sequence, nextjo, sessionph)
            newmsg = 'Congrats on a new job.\nThe JO is *' + nextjo + '*\n\n*Who is the customer?*\nEnter number or _NEW_ to add:\n'
            for adat in db.session.query(People.Company).filter(People.Ptype == 'Trucking').distinct():
                co = adat.Company
                adat2 = People.query.filter( (People.Company == co) & (People.Ptype == 'Trucking') ).first()
                if len(co) > 12:
                    co = co[0:12]
                sh = adat2.id
                newmsg = newmsg + f'*{sh}*: {co}\n'
            return newmsg

        elif sequence[1] != '1':
            compare = msg.lower()

            if sequence[1] == '0':
                # First time through people section, see if a name code is entered or new customer
                if 'new' in compare:
                    newmsg = 'OK, what is name of customer?'
                    sequence = sequence.replace('J0', 'J2')
                    putjo(sequence, jo, sessionph)
                else:
                    try:
                        pid = int(msg)
                        pdat = People.query.get(pid)
                        if pdat is not None:
                            sequence = sequence.replace('J0', 'J1')
                            putjo(sequence, jo, sessionph)
                            customer = pdat.Company
                            newmsg = f'Customer Found:\n*{customer}*\n'
                            pid = pdat.id
                            newmsg = newmsg + '\nNow Enter:\n*Booking#* (if export)\n*Container#* (if import)\n(Enter _N_ if none avail)'
                            appendline([customer, str(pid)], sessionph)
                        else:
                            newmsg = 'That customer not found.\nTry again, or enter NEW to'
                    except:
                        newmsg = 'Must enter a number that matches\nTry again, or enter NEW to'

            elif sequence[1] == '2':
                # This is start of sequence to enter a new customer
                customer = msg.title()
                ptest = People.query.filter(People.Company == customer).first()
                if ptest is None:
                    input = People(Company=customer, First=None, Middle=None, Last=None, Addr1=None, Addr2=None, Addr3=None, Idtype=None, Idnumber=None, Telephone=None,
                                   Email=None, Associate1=None, Associate2=None, Date1=today, Date2=None, Original=None, Ptype='Trucking', Temp1=None, Temp2=None, Accountid=None)
                    db.session.add(input)
                    db.session.commit()
                    pdat = People.query.filter(People.Company == customer).first()
                    pid = pdat.id
                    sequence = sequence.replace('J2', 'J3')
                    putjo(sequence, jo, sessionph)
                    appendline([customer, str(pid)], sessionph)
                    newmsg = f'Customer Added\n*{customer}*'
                    newmsg = newmsg + '\nEnter customer details:\n<street address>\n<city-state-zip>\n<phone>\n<email>'
                    newmsg = newmsg + '\nEnter *NO* to opt out\n\nOne item per line\nLeave blank as needed.'
                else:
                    newmsg = 'Customer already exists\nSetting up job using\n' + customer
                    sequence = sequence.replace('J2', 'J1')
                    putjo(sequence, jo, sessionph)
                    customer = ptest.Company
                    pid = ptest.id
                    appendline([customer, str(pid)], sessionph)
                    newmsg = newmsg + '\nNow Enter\n*Booking#* (if export)\n*Container#* (if import)\n(Enter a number or *N* if none avail)'
            # At this point have a new customer name, see if we want to add all the info here
            elif sequence[1] == '3':
                # Get the current info from text file:
                text = gettext(sessionph)
                customer = text[1].strip()
                pid = text[2]
                pid = int(pid)
                # No matter what the response we will move on from here so write out the txt file to move on
                sequence = sequence.replace('J3', 'J1')
                putjo(sequence, jo, sessionph)
                appendline([customer, str(pid), sessionph], sessionph)
                kickout = test_neg_response(compare)

                if kickout == 1:
                    # Time to move on, will put the details of customer in later
                    newmsg = 'Moving On....'
                else:
                    pdat = People.query.get(pid)
                    clines = msg.splitlines()
                    newmsg = 'Response Block Entered:'
                    for j, line in enumerate(clines):
                        if j == 0:
                            pdat.Addr1 = line
                            newmsg = newmsg + '\nAddr1: '+line
                        if j == 1:
                            pdat.Addr2 = line
                            newmsg = newmsg + '\nAddr2: '+line
                        if j == 2:
                            pdat.Telephone = line
                            newmsg = newmsg + '\nPhone: '+line
                        if j == 3:
                            pdat.Email = line
                            newmsg = newmsg + '\nEmail: '+line
                        db.session.commit()

                newmsg = newmsg + '\nNow Enter\n*Booking#* (if export)\n*Container#* (if import)\n(Enter a number or *N* if none avail)'

            return newmsg

        elif sequence[2] == '0':

            text = gettext(sessionph)
            customer = text[1].strip()
            pid = text[2]
            pid = int(pid)
            print(customer, pid)
            sequence = sequence.replace('J10', 'J11')
            if 'no' in compare or compare[0] == 'n':
                booking = 'TBD'
                container = 'TBD'
                newmsg = '_No Data Provided_'
            else:
                booking = msg.upper()
                container = 'TBD'
                newmsg = f'Booking *{booking}* Entered'

            #Check if this is a container:
            if len(msg) == 11:
                container = msg.upper()
                booking = ''
                newmsg = f'Container *{container}* Entered'

            input = Orders(Status='A0', Jo=jo, Load=None, Order=jo, Company=None, Location=None, Booking=booking, BOL=None, Container=container,
                           Date=today, Driver=None, Company2=None, Time=None, Date2=today, Time2=None, Seal=None, Pickup=None, Delivery=None,
                           Amount=None, Path=None, Original=None, Description=None, Chassis=None, Detention='0', Storage='0',
                           Release=0, Shipper=customer, Type=None, Time3=None, Bid=pid, Lid=None, Did=None, Label=None, Dropblock1=None, Dropblock2=None, Commodity=None, Packing=None,
                           Links=None, Hstat=-1,Istat=-1, Proof=None, Invoice=None, Gate=None, Package=None, Manifest=None, Scache=0,
                           Pcache=0,Icache=0, Mcache=0, Pkcache=0, QBi=0, InvoTotal=None)
            db.session.add(input)
            db.session.commit()

            putjo(sequence, jo, sessionph)
            return(newmsg+'\n\nEnter *Base Charge* for Job')

        elif sequence[3] == '0':

            try:
                price = float(compare)
                odat = Orders.query.filter(Orders.Jo == jo).first()
                odat.Amount = d2s(price)
                db.session.commit()
                sequence = sequence.replace('J110', 'J111')
                putjo(sequence, jo, sessionph)
                newmsg = f'Base Job Charge *${d2s(price)}* Entered\n\nNext, upload image to use as source document\nEnter *N* to continue without'
            except:
                newmsg = 'Could not understand that response\nLooking for *x.xx* entry..try again'

            return (newmsg)

        elif sequence[4] == '0':
            kickout = test_neg_response(compare)
            if kickout == 1:
                # Answer is no then move on to price entry
                sequence = sequence.replace('J1110', 'J1111')
                putjo(sequence, jo, sessionph)
                return('No File to Add\nWould you like to enter the pickup and delivery locations? (*y* or *n*)')
            else:
                # Start pickup entry session
                nolen = len(medialist)
                if nolen > 0:
                    newfile = save_Original(jo,medialist)
                    odat = Orders.query.filter(Orders.Jo == jo).first()
                    odat.Original = newfile
                    db.session.commit()
                    newmsg = 'File added to database.\nWould you like to enter the pickup and delivery locations? (*y* or *n*)'
                else:
                    newmsg = 'No file found...moving on...\nWould you like to enter the pickup and delivery locations? (*y* or *n*)'

                sequence = sequence.replace('J1110', 'J1111')
                putjo(sequence, jo, sessionph)

                return newmsg

        elif sequence[5] == '0':
            kickout = test_neg_response(compare)
            if kickout == 1:
                # Answer is no and nothing else to enter so end this sesion
                end_sequence(sessionph)
                return('OK, all done for now....')
            else:
                # Start pickup entry session
                sequence = sequence.replace('J11110', 'J11111')
                putjo(sequence, jo, sessionph)

                newmsg = 'OK, where is the pickup? (Enter a Number or _NEW_)\n'
                for adat in db.session.query(Drops.Entity).distinct():
                    co = adat.Entity
                    adat2 = Drops.query.filter(Drops.Entity == co).first()
                    if len(co) > 25:
                        co = co[0:25]
                    sh = adat2.id
                    newmsg = newmsg + f'*{sh}*: {co}\n'

                return newmsg

        elif sequence[6] == '0' or sequence[6] == '2':
            compare = msg.lower()

            if sequence[6] == '0':
                # First time through drop section, see if a number code is entered or new customer
                if 'new' in compare:
                    newmsg = f'Enter Pickup Location Details:\n\n'
                    newmsg = newmsg + '<name>\n<street address>\n<city-state-zip>\n<phone>\n<email>'
                    newmsg = newmsg + '\n\nOne item per line\nLeave blank as needed.'
                    sequence = sequence.replace('J111110', 'J111112')
                    putjo(sequence, jo, sessionph)
                    return newmsg
                else:
                    try:
                        pickup = int(msg.strip())
                        ddat = Drops.query.get(pickup)
                        if ddat is not None:
                            # Pickup found successful so update to next question
                            sequence = sequence.replace('J111110', 'J111111')
                            putjo(sequence, jo, sessionph)
                            idl = ddat.id
                            newdrop1 = ddat.Entity + '\n' + ddat.Addr1 + '\n' + ddat.Addr2 + '\n' + ddat.Phone + '\n' + ddat.Email

                            odat = Orders.query.filter(Orders.Jo == jo).first()
                            if odat is not None:
                                odat.Lid = idl
                                odat.Dropblock1 = newdrop1
                                odat.Company = ddat.Entity
                                db.session.commit()

                            newmsg = '_Pickup location found:_\n' + newdrop1 + '\n\nOK, where is the dropoff? (Enter a Number or _NEW_ )'
                        else:
                            newmsg = 'Not found, try again or Enter _NEW_ to create new LOCATION'
                    except:
                        newmsg = 'Must enter number code of pickup site...try again'

                    return newmsg

            elif sequence[6] == '2':
                # This is start of sequence to enter a new drop location
                getlines = msg.splitlines()
                try:
                    location = getlines[0].strip()
                except:
                    location = 'None'
                try:
                    addr1 = getlines[1].strip()
                except:
                    addr1 = ''
                try:
                    addr2 = getlines[2].strip()
                except:
                    addr2 = ''
                try:
                    phone = getlines[3].strip()
                except:
                    phone = ''
                try:
                    email = getlines[4].strip()
                except:
                    email = ''

                ptest = Drops.query.filter(Drops.Entity == location).first()

                if ptest is None:

                    input = Drops(Entity=location, Addr1=addr1, Addr2=addr2, Phone=phone, Email=email)
                    db.session.add(input)
                    db.session.commit()

                    ndat = Drops.query.filter(Drops.Entity == location).first()
                    did = ndat.id

                    newmsg = f'New Pickup Location Added:\n{location}'
                    newmsg = newmsg + f'\nAddr1: {addr1}\nAddr2: {addr2}\nPhone: {phone}\nEmail: {email}'
                    newmsg = newmsg + f'\n\nEnter *{did}* to use this location as Pickup Selection...'

                    sequence = sequence.replace('J111112', 'J111110')
                    putjo(sequence, jo, sessionph)

                else:
                    newmsg = f'Drop Location *{location}* already exists\nTry again....\n'

                return newmsg

        elif sequence[7] == '0' or sequence[7] == '2':
            compare = msg.lower()

            if sequence[7] == '0':
                # First time through drop section, see if a number code is entered or new customer
                if 'new' in compare:
                    newmsg = f'Enter New Dropoff Location Details:\n\n'
                    newmsg = newmsg + '<name>\n<street address>\n<city-state-zip>\n<phone>\n<email>'
                    newmsg = newmsg + '\n\nOne item per line\nLeave blank as needed.'
                    sequence = sequence.replace('J1111110', 'J1111112')
                    putjo(sequence, jo, sessionph)
                    return newmsg
                else:
                    try:
                        pickup = int(msg.strip())
                        ddat = Drops.query.get(pickup)
                        if ddat is not None:
                            idl = ddat.id
                            newdrop1 = ddat.Entity + '\n' + ddat.Addr1 + '\n' + ddat.Addr2 + '\n' + ddat.Phone + '\n' + ddat.Email

                            odat = Orders.query.filter(Orders.Jo == jo).first()
                            if odat is not None:
                                odat.Did = idl
                                odat.Dropblock2 = newdrop1
                                odat.Company2 = ddat.Entity
                                db.session.commit()

                            newmsg = '_Dropoff location found:_\n'+newdrop1
                            end_sequence(sessionph)
                            return (newmsg + '\n\nOK, all done for now....')
                        else:
                            return('No Dropoff Found...Try Again')
                    except:
                        newmsg = 'Must enter number code of drop site...try again'
                        return newmsg

            elif sequence[7] == '2':
                # This is start of sequence to enter a new drop location
                getlines = msg.splitlines()
                try:
                    location = getlines[0].strip()
                except:
                    location = 'None'
                try:
                    addr1 = getlines[1].strip()
                except:
                    addr1 = ''
                try:
                    addr2 = getlines[2].strip()
                except:
                    addr2 = ''
                try:
                    phone = getlines[3].strip()
                except:
                    phone = ''
                try:
                    email = getlines[4].strip()
                except:
                    email = ''

                ptest = Drops.query.filter(Drops.Entity == location).first()

                if ptest is None:

                    input = Drops(Entity=location, Addr1=addr1, Addr2=addr2, Phone=phone, Email=email)
                    db.session.add(input)
                    db.session.commit()

                    ndat = Drops.query.filter(Drops.Entity == location).first()
                    did = ndat.id

                    newmsg = f'New Dropoff Location Added:\n{location}'
                    newmsg = newmsg + f'\nAddr1: {addr1}\nAddr2: {addr2}\nPhone: {phone}\nEmail: {email}'
                    newmsg = newmsg + f'\n\nEnter *{did}* to use this location as Dropoff Selection...'

                    sequence = sequence.replace('J1111112', 'J1111110')
                    putjo(sequence, jo, sessionph)

                else:
                    newmsg = f'Drop Location *{location}* already exists\nTry again....\n'

                return newmsg



        else:
            end_sequence(sessionph)
            return('OK, all done entering job....')

    elif vintest == 1:

        print('Got to vintest', vinlist)
        txt_file = addpath(f'tmp/{scac}/data/processing/vins.txt')
        print(txt_file)

        try:
            os.remove(txt_file)
        except IOError:
            print('File already removed')

        with open(txt_file, 'a+') as f:
            f.write(sessionph + '\n')
            for vin in vinlist:
                vin = vin.strip()
                f.write(vin+'\n')
        f.close()

        thisip = os.environ['PUBLICIP']
        #thisip = '10.0.0.105'
        print('thisip',thisip)
        tout = subprocess.check_output(['scp',txt_file,'mark@'+thisip+':/home/mark/flask/crontasks/incoming/whatsapp/vins.txt'])

        return('Scraping VIN now for Year, Make, Model, Weight, Avg Cost...\nTakes about 1 minute...')


    else:
        # Provide the main menu
        end_sequence(sessionph)
        newmsg = '*MENU*'
        newmsg = newmsg + '\n*JOB*: Enter New Truck Job'
        newmsg = newmsg + '\n*GLO*: Global Job via Booking'
        newmsg = newmsg + '\n*QUO*: Quote Job'
        newmsg = newmsg + '\n*OUT*: Find Whats Out'
        newmsg = newmsg + '\n*CUS*: New Customer'
        newmsg = newmsg + '\n*DRP*: Drop Address'
        newmsg = newmsg + '\n*MAN*: Make Manifest'
        newmsg = newmsg + '\n*INV*: Make Invoice'
        newmsg = newmsg + '\n*BAL*: Bank Balance'
        newmsg = newmsg + '\n*VIN*: Enter 17-Digit VIN'




        if 'vin' in compare and len(compare)==3:
            newmsg = 'Enter your VIN...'

        return newmsg
