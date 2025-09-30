from flask import request
import smtplib
import mimetypes
from email.mime.multipart import MIMEMultipart
from email import encoders
from email.message import Message
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
import ntpath
import shutil
import os
from webapp.CCC_system_setup import websites, passwords, companydata, scac, addpath
from webapp.CCC_system_setup import usernames as em
from webapp import db
from webapp.models import People, Orders, Ardata
from webapp.viewfuncs import stripper, hasinput

import datetime
today = datetime.datetime.today()
today_str = today.strftime('%d %b %Y')

def check_person(info):
    name = info[4]
    email = info[2]
    phone = info[3]
    message = info[1]
    pdata = People.query.filter((People.Ptype == 'Contact') & (People.Company == name)).all()
    return len(pdata)

def add_person(info):
    name = info[4]
    email = info[2]
    phone = info[3]
    message = info[1]
    input = People(Company=name, First=None, Middle=None, Last=None, Addr1=None, Addr2=None, Addr3=None,
                   Idtype=None, Idnumber=None, Telephone=phone,
                   Email=email, Associate1=None, Associate2=None, Date1=today, Date2=None, Source=message,
                   Ptype='Contact', Temp1=None, Temp2=None, Accountid=None)
    db.session.add(input)
    db.session.commit()

def emaildata_update():
    #print('running email update')
    etitle = request.values.get('edat0')
    ebody = request.values.get('edat1')
    outfile = request.values.get('edat7')
    sourcefile = request.values.get('edat6')
    folder = request.values.get('edat8')
    emailin1 = request.values.get('edat2')
    emailin2 = request.values.get('edat3')
    emailcc1 = request.values.get('edat4')
    emailcc2 = request.values.get('edat5')
    emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2, sourcefile, outfile, folder]
    return emaildata

def email_template(type, info):
    if type == 'class8demo':
        etitle = 'Demonstration Request for Class8 Software'
        ebody = f'Your request for a demonstration has been received. We will confirm your appointment upon receipt and reveiw.' \
                f'<br><br>Date and Time: {info[0]}<br>Address: {info[1]}<br>Your email: {info[2]}<br>Your phone:{info[3]}<br>' \
                f'Contact Name: {info[4]}<br><br>We appreciate this opportunity and look forward t speaking with you.'
        emailin1 = f'{info[2]}'
        emailin2 = ''
        emailcc1 = em['info']
        emailcc2 = ''
        aname = ''
        emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2, aname]

    if type == 'contact':
        etitle = 'Message to NixonAI Received'
        ebody = f'This is a confirmation that your contact information has been received. We will be in touch as soon as possible after we receive this notification.' \
                f'<br><br>Date and Time: {info[0]}<br>Contact Name: {info[4]}<br>Your email: {info[2]}<br>Your phone:{info[3]}<br>' \
                f'Your Message: {info[1]}<br><brWe appreciate this opportunity and look forward t speaking with you.'
        emailin1 = f'{info[2]}'
        emailin2 = ''
        emailcc1 = em['info']
        emailcc2 = ''
        aname = ''
        emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2, aname]

    return emaildata

def etemplate_suminv(eprof, sdat):
    if eprof == 'suminv':
        pdat = People.query.get(sdat.Pid)
        if pdat is not None:
            estatus, epod, eaccts = pdat.Email, pdat.Associate1, pdat.Associate2
            estatus, epod, eaccts = stripper(estatus), stripper(epod), stripper(eaccts)
        shipper = pdat.Company
        etitle = f'Summary Invoice {sdat.Si} {today_str}'
        ebody = f'Dear {shipper},\n\nAn invoice summary has been created for completed jobs.\n\nWe greatly appreciate your business.'
        aname = sdat.Source
        emailin1 = estatus
        emailin2 = eaccts
        emailcc1 = em['info']
        emailcc2 = em['expo']
        outname = f'Invoice_Summary_{sdat.Si}.pdf'
        emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2, aname, outname, 'vinvoice']
        return emaildata

    else:
        etitle = 'Unknown'
        ebody = 'Could not determine the type of package being emailed here.'

    try:
        pdat = People.query.get(sdat.Pid)
        emailin1 = str(pdat.Email)
    except:
        emailin1 = 'Not Found'

    emailin2 = ''
    emailcc1 = em['info']
    emailcc2 = em['serv']
    emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2, '']

    return emaildata

def etemplate_truck(eprof,odat):
    cdata = companydata()
    bid = odat.Bid
    shipper = odat.Shipper
    jo = odat.Jo

    signature = cdata[2] + '\n' + cdata[5] + '\n' + cdata[6] + '\n' + cdata[7]

    od, bol, con, bk = odat.Order, odat.BOL, odat.Container, odat.Booking
    od, bol, con, bk = stripper(od), stripper(bol), stripper(con), stripper(bk)
    if bol is None:
        keyval = bk
    else:
        if len(bol)< 5:
            keyval = bk
        else:
            keyval = bol
    dblk = odat.Dropblock2
    if dblk is not None:
        dblk = dblk.splitlines()
    else:
        dblk = ['','','','','']
    pdat = People.query.get(bid)
    if pdat is None:
        pdat = People.query.filter(People.Company == shipper).first()
    if pdat is not None:
        estatus, epod, eaccts = pdat.Email, pdat.Associate1, pdat.Associate2
        estatus, epod, eaccts = stripper(estatus), stripper(epod), stripper(eaccts)
    else:
        estatus, epod, eaccts = '', '', ''

    if eprof== 'eprof1':
        etitle = f'Update on Order: {od} | {keyval} | {con}'
        ebody = f'Dear {odat.Shipper},\n\nOur trucker is at the delivery site:\n\t\t{dblk[0]}\n\t\t{dblk[1]}\n\t\t{dblk[2]}\nWe will send a POD as soon as one can be obtained.\n\nSincerely,\n\n{signature}'
        aname = 'none'
        emailin1 = estatus
        emailin2 = ''
        emailcc1 = em['info']
        emailcc2 = ''
        emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2, aname]
        return emaildata

    elif eprof == 'eprof2':
        etitle = f'Update on Order: {od} | {keyval} | {con}'
        ebody = f'Dear {odat.Shipper},\n\nThe subject container has been pulled from the port. Delivery is scheduled for {odat.Date2} to:\n\t\t{dblk[0]}\n\t\t{dblk[1]}\n\t\t{dblk[2]}\nWe will send a POD as soon as delivery is complete.\n\nSincerely,\n\n{signature}'
        aname = odat.Gate
        emailin1 = estatus
        emailin2 = ''
        emailcc1 = em['info']
        emailcc2 = ''
        emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2, aname]
        return emaildata

    elif eprof == 'eprof3':
        etitle = f'Invoice for Completed Order: {od} | {keyval} | {con}'
        ebody = f'Dear {odat.Shipper},\n\nThe subject order has been completed, and your invoice for services is attached.\n\nWe greatly appreciate your business.\n\nSincerely,\n\n{signature}'
        aname = odat.Invoice
        aname = aname.replace('INV', 'Invoice_')
        emailin1 = estatus
        emailin2 = eaccts
        emailcc1 = em['info']
        emailcc2 = em['expo']
        emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2, aname, aname, 'VInvoice']
        return emaildata

    elif eprof == 'eprof4':
        etitle = f'Proof for Completed Order: {od} | {keyval} | {con}'
        ebody = f'Dear {odat.Shipper},\n\nThe subject order has been completed, and your proof of delivery is attached.\n\nPlease do not hesitate to respond if you have any questions.\n\nSincerely,\n\n{signature}'
        aname = odat.Proof
        emailin1 = estatus
        emailin2 = epod
        emailcc1 = em['info']
        emailcc2 = em['expo']
        emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2, aname]
        return emaildata

    elif eprof == 'eprof5':
        etitle = f'Invoice & Proof for Completed Order: {od} | {keyval} | {con}'
        ebody = f'Dear {odat.Shipper},\n\nThe subject order has been completed, and your invoice with proof of delivery is attached.\n\nPlease do not hesitate to respond if you have any questions.\n\nSincerely,\n\n{signature}'
        aname = f'Package_{odat.Jo}.pdf'
        emailin1 = estatus
        emailin2 = eaccts
        emailcc1 = em['info']
        emailcc2 = em['expo']
        emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2, aname]
        return emaildata

    elif eprof == 'eprof6':
        etitle = f'Invoice Package for Completed Order: {od} | {keyval} | {con}'
        ebody = f'Dear {odat.Shipper},\n\nThe subject order has been completed, and your invoice package is attached.\n\nPlease do not hesitate to respond if you have any questions.\n\nSincerely,\n\n{signature}'
        aname = f'Package_{odat.Jo}.pdf'
        emailin1 = estatus
        emailin2 = eaccts
        emailcc1 = em['info']
        emailcc2 = em['expo']
        emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2, aname]
        return emaildata

    elif eprof == 'invoice':
        etitle = f'Invoice for Completed Order: {od} | {keyval} | {con}'
        ebody = f'Dear {odat.Shipper},\n\nThe subject order has been completed, and your invoice for services is attached.\n\nWe greatly appreciate your business.'
        aname = odat.Invoice
        emailin1 = estatus
        emailin2 = eaccts
        emailcc1 = em['invo']
        emailcc2 = ''
        emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2, aname, aname, 'vInvoice']
        return emaildata


    elif eprof == 'paidinvoice':
        etitle = f'Payment Received on Invoice {odat.Jo} for Completed Order: {od} | {keyval} | {con}'
        ebody = f'Dear {odat.Shipper},\n\nYour payment has been received, and your stamped invoice is attached.\n\nWe greatly appreciate your business.\n\nSincerely,\n\n{signature}'
        #aname = odat.Invoice
        #aname = aname.replace('INV', 'Paid_Invoice_')
        aname = odat.PaidInvoice
        emailin1 = estatus
        emailin2 = eaccts
        emailcc1 = em['invo']
        emailcc2 = ''
        emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2, aname]
        return emaildata

    elif eprof == 'packages':
        etitle = f'{scac} Invoice Package for Completed Orders: {od} | {keyval} | {con}'
        ebody = f'Dear {odat.Shipper},\n\nAn invoice package is enclosed for your review.\nWe greatly appreciate your business.\n\nSincerely,\n\n{signature}'
        aname = f'Package_{odat.Jo}.pdf'
        emailin1 = estatus
        emailin2 = eaccts
        emailcc1 = em['invo']
        emailcc2 = ''
        emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2, aname]
        return emaildata

    elif eprof == 'invopackage':
        etitle = f'{scac} Invoice Package {odat.Package}'
        ebody = f'Dear {odat.Shipper},\n\nAn invoice package is enclosed for your review.\nWe greatly appreciate your business.\n\nSincerely,\n\n{signature}'
        aname = odat.Package
        emailin1 = estatus
        emailin2 = eaccts
        emailcc1 = em['invo']
        emailcc2 = ''
        emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2, aname]
        return emaildata

    elif eprof == 'Custom' or eprof == 'Custom-Invoice':
        if eprof == 'Custom-Invoice':
            etitle = f'{scac} Invoice Package For: {od} | {keyval} | {con}'
            ebody = f'Dear {odat.Shipper},\n\nThis invoice package is enclosed for your review.\nWe greatly appreciate your business.\n\nSincerely,\n\n{signature}'
        else:
            etitle = f'{scac} Document Package For: {od} | {keyval} | {con}'
            ebody = f'Dear {odat.Shipper},\n\nThis document package is enclosed for your review.\nWe greatly appreciate your business.\n\nSincerely,\n\n{signature}'
        aname = odat.Package
        emailin1 = estatus
        emailin2 = eaccts
        emailcc1 = em['invo']
        emailcc2 = ''
        outname = f'Package_{odat.Jo}.pdf'
        emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2, aname, outname, 'vPackage']
        return emaildata

    elif eprof == 'Signed Load Con':
        if hasinput(con):
            etitle = f'Signed Load Confirmation: {od} | {keyval} | {con}'
        else: etitle = f'Signed Load Confirmation: {od} | {keyval}'
        ebody = f'Dear {odat.Shipper},\n\nThis load confirmation has been received with signed copy attached.'
        sourcename = odat.Package
        folder = 'vPackage'
        outname = f'Signed_Load_Confirmation_{od}.pdf'
        emailin1 = estatus
        emailin2 = ''
        emailcc1 = em['info']
        emailcc2 = ''
        emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2, sourcename, outname, folder]
        return emaildata

    elif eprof == 'Update w/Source':
        etitle = f'Update on Order: {od} | {keyval} | {con}'
        ebody = f'Dear {odat.Shipper},\n\nDelivery of this load is scheduled for {odat.Date2} to:\n\t\t{dblk[0]}\n\t\t{dblk[1]}\n\t\t{dblk[2]}\nWe will send a POD as soon as delivery is complete.'
        aname = odat.Source
        emailin1 = estatus
        emailin2 = ''
        emailcc1 = em['info']
        emailcc2 = ''
        emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2, aname, aname, 'vPackage']
        return emaildata

    elif eprof == 'Update w/Proof':
        etitle = f'Proof for Order: {od} | {keyval} | {con}'
        ebody = f'Dear {odat.Shipper},\n\nThe subject order has been completed, and your proof of delivery is attached.\n\nPlease do not hesitate to respond if you have any questions.'
        aname = odat.Proof
        emailin1 = estatus
        emailin2 = ''
        emailcc1 = em['info']
        emailcc2 = ''
        emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2, aname, aname, 'vPackage']
        return emaildata

    elif eprof == 'Update w/Invoice':
        etitle = f'Invoice for Order: {od} | {keyval} | {con}'
        ebody = f'Dear {odat.Shipper},\n\nThe subject order has been completed, and your invoice for services is attached.\n\nWe greatly appreciate your business.'
        aname = odat.Invoice
        aname = aname.replace('INV','Invoice_')
        emailin1 = estatus
        emailin2 = ''
        emailcc1 = em['invo']
        emailcc2 = ''
        emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2, aname, aname, 'vPackage']
        return emaildata

    elif eprof == 'Paid Invoice':
        etitle = f'Payment Received on Invoice {odat.Jo} for Completed Order: {od} | {keyval} | {con}'
        ebody = f'Dear {odat.Shipper},\n\nYour payment has been received, and your stamped invoice is attached.\n\nWe greatly appreciate your business.\n\nSincerely,\n\n{signature}'
        #aname = odat.Invoice
        #aname = aname.replace('INV', 'Paid_Invoice_')
        aname = odat.PaidInvoice
        #print(f'aname here is {aname} {odat.PaidInvoice} {odat.Jo} {odat.Source}')
        emailin1 = estatus
        emailin2 = eaccts
        emailcc1 = em['invo']
        emailcc2 = ''
        emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2, aname, aname, 'vPaidInvoice']
        return emaildata

    elif eprof == 'Update w/Gate':
        etitle = f'Gate Tickets: {od} | {keyval} | {con}'
        ebody = f'Dear {odat.Shipper},\n\nThe gate tickets for the subject order are attached.'
        aname = odat.Gate
        emailin1 = estatus
        emailin2 = ''
        emailcc1 = em['info']
        emailcc2 = ''
        emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2, aname, aname, 'vPackage']
        return emaildata

    elif eprof == 'Completed IP':
        etitle = f'Invoice and Proof for Order: {od} | {keyval} | {con}'
        ebody = f'Dear {odat.Shipper},\n\nThe subject order has been completed, and your invoice package for services is attached.\n\nWe greatly appreciate your business.'
        aname = odat.Package
        emailin1 = estatus
        emailin2 = eaccts
        emailcc1 = em['invo']
        emailcc2 = ''
        outname = f'Invoice-Proof_{odat.Jo}.pdf'
        emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2, aname, outname, 'vPackage']
        return emaildata

    elif eprof == 'Completed IPG':
        etitle = f'Invoice/Proof/Gate for Order: {od} | {keyval} | {con}'
        ebody = f'Dear {odat.Shipper},\n\nThe subject order has been completed, and your invoice package for services is attached.\n\nWe greatly appreciate your business.'
        aname = odat.Package
        emailin1 = estatus
        emailin2 = eaccts
        emailcc1 = em['invo']
        emailcc2 = ''
        outname = f'Invoice-Package_{odat.Jo}.pdf'
        emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2, aname, outname, 'vPackage']
        return emaildata

    elif eprof == 'Completed IPGS':
        etitle = f'Invoice Package for Order: {od} | {keyval} | {con}'
        ebody = f'Dear {odat.Shipper},\n\nThe subject order has been completed, and your invoice package for services is attached.\n\nWe greatly appreciate your business.'
        aname = odat.Package
        emailin1 = estatus
        emailin2 = eaccts
        emailcc1 = em['invo']
        emailcc2 = ''
        outname = f'Invoice-Package_{odat.Jo}.pdf'
        emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2, aname, outname, 'vPackage']
        return emaildata

    elif eprof == 'suminv':
        etitle = f'Summary Invoice {odat.Si} {today_str}'
        ebody = f'Dear {odat.Shipper},\n\nThe subject order has been completed, and your invoice package for services is attached.\n\nWe greatly appreciate your business.'
        aname = odat.Source
        emailin1 = estatus
        emailin2 = eaccts
        emailcc1 = em['invo']
        emailcc2 = ''
        outname = f'Invoice_Summary_{odat.Si}_{today_str}.pdf'
        emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2, aname, outname, 'vinvoice']
        return emaildata

    elif eprof == 'quote':
        etitle = cdata[2] + ' Quote: ' + jo
        ebody = 'Dear Customer:\n\nYour quote is attached. Please sign and return at your earliest convenience.\n\nWe look forward to doing business with you.\n\nSincerely,\n\n' + \
                cdata[3] + '\n\n\n' + cdata[4] + '\n' + cdata[2] + '\n' + cdata[5] + '\n' + cdata[6] + '\n' + cdata[7]

    else:
        etitle = 'Unknown'
        ebody = 'Could not determine the type of package being emailed here.'

    try:
        pdat = People.query.get(bid)
        emailin1 = str(pdat.Email)
    except:
        emailin1 = 'Not Found'
    emailin2 = ''
    emailcc1 = em['invo']
    emailcc2 = ''
    emaildata = [etitle, ebody, emailin1, emailin2, emailcc1, emailcc2, '']

    return emaildata





    
def email_app_exporter(pdata):
    

    ourserver = websites['mailserver']
    cdat = companydata()
    
    for pdat in pdata:
        ptype=pdat.Ptype
        if ptype=='exporter':
            emailin=pdat.Email
            #print('Eporter email=',emailin)
            exporter=pdat.First+' '+pdat.Middle+' '+pdat.Last
            exporter=exporter.replace('  ',' ')
            idn=pdat.id

    if emailin is None or emailin=='None' or len(emailin)<5 or '@' not in emailin:
        emailin = usernames['expo']
        code='Either no email or a bad email was provided'
        
    #emailto = "export@firsteaglelogistics.com"
    emailfrom = emails['expo']
    emailto = emailin
    #emailcc = "info@firsteaglelogistics.com"
    emailcc1 = emails['info']
    emailcc2 = emails['serv']
    
    
    #fileToSend = absdocref
    username = emails[2]
    password = passwords['expo']

    msg = MIMEMultipart()
    msg["From"] = emailfrom
    msg["To"] = emailto
    msg["Cc"] = emailcc1
    msg["Cc"] = emailcc2
    msg["Subject"] = f'{cdat[0]} Application Received'

    from_dom = emailfrom.split('@')[1]
    #print(f'from email_app_exporter in class8-utls_email: the domain is: {from_dom}')
    msg['Date'] = formatdate()
    msg['Message-ID'] = make_msgid(domain=from_dom)

    body = 'Dear '+exporter+':\n\nThis email confirms receipt of your international shipping application with confirmation code Fapp'+str(idn)
    body = body+', and the following summarizes the information we received from you:\n\n'
    for pdat in pdata:
        ptype=pdat.Ptype
        if ptype=='exporter':

            body = body+'Exporter: '+pdat.First+' '+pdat.Middle+' '+pdat.Last+'\n'
            body = body+'Address:'+pdat.Addr1+' '+pdat.Addr2+' '+pdat.Addr3+'\n'
            body = body+'ID:'+pdat.Idtype+' '+pdat.Idnumber+'\n'
            body = body+'Telephone:'+pdat.Telephone+'\n'
            body = body+'Email: '+pdat.Email+'\n\n'
            
        if ptype=='consignee':
            
            body = body+'Consignee: ' + pdat.First +' '+ pdat.Middle +' '+ pdat.Last +'\n'
            body = body+'Address:'+pdat.Addr1+' '+pdat.Addr2+' '+pdat.Addr3+'\n'
            body = body+'Telephone:'+pdat.Telephone+'\n'
            body = body+'Email: '+pdat.Email+'\n\n'
            
        if ptype=='notify':
            
            body = body+'Notify Party: ' + pdat.First +' '+ pdat.Middle +' '+ pdat.Last +'\n'
            body = body+'Address:'+pdat.Addr1+' '+pdat.Addr2+' '+pdat.Addr3+'\n'
            body = body+'Telephone:'+pdat.Telephone+'\n'
            body = body+'Email: '+pdat.Email+'\n\n'

    body = body+'\n\nSincerely,\n\nNorma Ghanem\nFirst Eagle Logistics, Inc.\n505 Hampton Park Blvd Unit O\nCapitol Heights,MD 20743\n301 516 3000'
    msg.attach(MIMEText(body, 'plain'))

    #attachment = open(fileToSend, "rb")
 
    #part = MIMEBase('application', 'octet-stream')
    #part.set_payload((attachment).read())
    #encoders.encode_base64(part)
    #part.add_header('Content-Disposition', "attachment; filename= %s" % fileToSend)
 
    #msg.attach(part)
    [host, port] = ourserver.split(':')
    server = smtplib.SMTP(host, port)
    #server = smtplib.SMTP(ourserver)
    #server.starttls()
    server.login(username,password)
    emailto = [emailto, emailcc1, emailcc2]
    server.sendmail(emailfrom, emailto, msg.as_string())
    server.quit()
    
    #os.remove(newfile)
    
    
def email_app(pdat):

    emails,passwds,ourserver=emailvals()

    emailin=pdat.Email
    if emailin is None or emailin=='None' or len(emailin)<5 or '@' not in emailin:
        emailin = emails[4]
        code='Either no email or a bad email was provided'
        
    #emailto = "export@firsteaglelogistics.com"
    emailfrom = emails[2]
    emailto = emailin
    #emailcc = "info@firsteaglelogistics.com"
    emailcc1 = emails[0]
    emailcc2 = emails[1]
    
    
    #fileToSend = absdocref
    username = emails[2]
    password = passwds[0]

    msg = MIMEMultipart()
    msg["From"] = emailfrom
    msg["To"] = emailto
    msg["Cc"] = emailcc1
    msg["Cc"] = emailcc2
    msg["Subject"] = 'First Eagle Logistics Application Received'

    from_dom = emailfrom.split('@')[1]
    #print(f'from email_app in class8-utls_email: the domain is: {from_dom}')
    msg['Date'] = formatdate()
    msg['Message-ID'] = make_msgid(domain=from_dom)

    body = 'Dear '+pdat.Company+':\n\nThis email confirms receipt of your application with confirmation code Fapp'+str(pdat.id)
    body = body+', and the following summarizes the information we received from you:\n\n'
    body = body+'Name: '+pdat.Company+'\n'
    body = body+'Address:'+pdat.Addr1+' '+pdat.Addr2+'\n'
    body = body+'CDL:'+pdat.Idtype+' '+pdat.Idnumber+'\n'
    body = body+'Telephone:'+pdat.Telephone+'\n'
    body = body+'Email: '+pdat.Email+'\n'
    body = body+'TWIC Info: '+pdat.Associate1+'\n'
    body = body+'Medical: '+pdat.Associate2+'\n'
    body = body+'Experience: '+pdat.Temp1+'\n\n'
    body = body+'We will review your information promptly and contact very soon.'
    body = body+'\n\nSincerely,\n\nNorma Ghanem\nFirst Eagle Logistics, Inc.\n505 Hampton Park Blvd Unit O\nCapitol Heights,MD 20743\n301 516 3000'
    msg.attach(MIMEText(body, 'plain'))

    #attachment = open(fileToSend, "rb")
 
    #part = MIMEBase('application', 'octet-stream')
    #part.set_payload((attachment).read())
    #encoders.encode_base64(part)
    #part.add_header('Content-Disposition', "attachment; filename= %s" % fileToSend)
 
    #msg.attach(part)
    [host, port] = ourserver.split(':')
    server = smtplib.SMTP(host, port)
    #server = smtplib.SMTP(ourserver)
    #server.starttls()
    server.login(username,password)
    emailto = [emailto, emailcc1, emailcc2]
    server.sendmail(emailfrom, emailto, msg.as_string())
    server.quit()
    
    #os.remove(newfile)

def update_ardata(etitle, ebody, eto, ecc, docref, newfile, emailfrom, lastpath, sids):
    jolist = []
    conlist = []
    shipper = None
    for sid in sids:
        odat = Orders.query.get(sid)
        if odat is not None:
            shipper = odat.Shipper
            jo = odat.Jo
            con = odat.Container
            jolist.append(jo)
            conlist.append(con)
            odat.InvoDate = today
            #Important this updates the orders for the final summary invoice sent out
            if 'SI' in docref:
                odat.Package = docref
    db.session.commit()

    ncl = f'{conlist}'
    jl = f'{jolist}'
    filtered_eto = [item for item in eto if item.strip()]
    filtered_ecc = [item for item in ecc if item.strip()]
    etf = f'{filtered_eto}'
    ecf = f'{filtered_ecc}'
    #print((f'the eto is {etf}')

    input = Ardata(Etitle=etitle, Ebody=ebody, Emailto=etf, Emailcc=ecf, Sendfiles=f'[{docref}]',
                   Sendasfiles=f'[{newfile}]', Jolist=jl, Emailtype='Invoice', Mid=None,
                   Customer=shipper, Container=ncl, Date1=today, Datelist=None, From=emailfrom, Box='SENT')
    db.session.add(input)
    db.session.commit()

def invoice_mimemail(docref, err, lastpath, sids):
    cdata = companydata()

    company_info = f'{cdata[2]}<br>{cdata[8]}<br>{cdata[16]}<br><br>{cdata[13]}<br><br>{cdata[14]}<br><br>{cdata[15]}'
    closing = f'  <br><br>Kind Regards,<br>Accounting Team<br>{company_info}'

    ourserver = websites['mailserver']

    emailin1=request.values.get('edat2')
    emailin2=request.values.get('edat3')
    emailcc1=request.values.get('edat4')
    emailcc2=request.values.get('edat5')
    etitle=request.values.get('edat0')
    ebody=request.values.get('edat1')
    newfile = request.values.get('edat6')

    ebody = f'{ebody} {closing}'

    if 'Proof' in docref:
        lastpath = 'vProofs'
    elif 'Manifest' in docref:
        lastpath = 'vManifest'

    if newfile != 'none':
        cfrom = addpath(f'static/{scac}/data/{lastpath}/{docref}')
        #print(cfrom,newfile)
        shutil.copy(cfrom,newfile)

    #emailto = "export@firsteaglelogistics.com"
    emailfrom = em['invo']
    username = em['invo']
    password = passwords['invo']

    msg = MIMEMultipart()

    eto = [f'{emailin1}', f'{emailin2}']
    ecc = [f'{emailcc1}', f'{emailcc2}']

    tolist, cclist = '', ''
    emailto = []
    for emt in eto:
        if hasinput(emt) and emt != '':
            tolist = f'{tolist}, {emt}'
            emailto.append(emt)
    for emt in ecc:
        if hasinput(emt) and emt != '':
            cclist = f'{cclist}, {emt}'
            emailto.append(emt)

    from_dom = emailfrom.split('@')[1]
    #print(f'from invoice_mimemail in class8-utls_email: the domain is: {from_dom}')

    msg["From"] = emailfrom
    msg["To"] = tolist
    msg["CC"] = cclist
    msg["Subject"] = etitle
    msg['Date'] = formatdate()
    msg['Message-ID'] = make_msgid(domain=from_dom)

    ebody = ebody.replace('\n', '<br>')

    msg.attach(MIMEText(ebody, 'html'))
    #msg.attach(MIMEText(signature, 'html'))

    if newfile != 'none':
        attachment = open(newfile, "rb")
        part = MIMEBase('application', 'octet-stream')
        part.set_payload((attachment).read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', "attachment; filename= %s" % newfile)
        msg.attach(part)
        #attachment.close()
        os.remove(newfile)

    [host, port] = ourserver.split(':')
    server = smtplib.SMTP(host, port)
    #server = smtplib.SMTP(ourserver)
    server.starttls()
    code, check = server.login(username,password)
    #print('check', code, check.decode("utf-8"))
    err.append(f"Email Login: {check.decode('utf-8')}")
    err.append(f"Email To: {emailin1} sent")
    err.append(f"Email From: {emailfrom}")
    server.sendmail(emailfrom, emailto, msg.as_string())

    server.quit()

    update_ardata(etitle, ebody, eto, ecc, docref, newfile, emailfrom, lastpath, sids)

    return err

def info_mimemail(emaildata, sids):
    err=[]
    cdata = companydata()
    company_info = f'{cdata[2]}<br>{cdata[8]}<br>{cdata[16]}<br><br>{cdata[13]}<br><br>{cdata[14]}<br><br>{cdata[15]}'
    closing = f'<br><br>Accounting Team<br>{company_info}'

    #print((f'for info mimemail sids is {sids}')

    ourserver = websites['mailserver']
    etitle, ebody, emailin1, emailin2, emailcc1, emailcc2, sourcename, sendname, folder = emaildata

    #emailto = "export@firsteaglelogistics.com"
    emailfrom = em['invo']
    username = em['invo']
    password = passwords['invo']

    ebody = f'{ebody} {closing}'

    msg = MIMEMultipart()

    eto = [f'{emailin1}', f'{emailin2}']
    ecc = [f'{emailcc1}', f'{emailcc2}']

    tolist, cclist = '', ''
    emailto = []
    for emt in eto:
        if hasinput(emt) and emt != '':
            tolist = f'{tolist}, {emt}'
            emailto.append(emt)
    for emt in ecc:
        if hasinput(emt) and emt != '':
            cclist = f'{cclist}, {emt}'
            emailto.append(emt)

    from_dom = emailfrom.split('@')[1]
    #print(f'from info_mimemail in class8-utls_email: the domain is: {from_dom}')

    msg["From"] = emailfrom
    msg["To"] = tolist
    msg["CC"] = cclist
    msg["Subject"] = etitle
    msg['Date'] = formatdate()
    msg['Message-ID'] = make_msgid(domain=from_dom)

    ebody = ebody.replace('\n', '<br>')

    # See if there is an attachment

    if sourcename != 'No Attachment':
        cfrom = addpath(f'static/{scac}/data/{folder}/{sourcename}')
        newfile = addpath(f'static/{scac}/data/temp/{sendname}')
        #print(cfrom,newfile)
        shutil.copy(cfrom,newfile)

        attachment = open(newfile, "rb")
        part = MIMEBase('application', 'octet-stream')
        part.set_payload((attachment).read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', "attachment; filename= %s" % sendname)
        msg.attach(part)
        #attachment.close()
        #os.remove(newfile)

    msg.attach(MIMEText(ebody, 'html'))

    [host, port] = ourserver.split(':')
    server = smtplib.SMTP(host, port)
    #server = smtplib.SMTP(ourserver)
    server.starttls()
    code, check = server.login(username,password)
    #print('check', code, check.decode("utf-8"))
    err.append(f"Email Login: {check.decode('utf-8')}")
    err.append(f"Email To: {emailin1} sent")
    err.append(f"Email From: {emailfrom}")
    server.sendmail(emailfrom, emailto, msg.as_string())

    server.quit()

    update_ardata(etitle, ebody, eto, ecc, sourcename, sendname, emailfrom, 'vPackage', sids)

    return err

def html_mimemail(emaildata):
    err=[]
    ourserver = websites['mailserver']
    #emaildata = [etitle, ebody, eto, ecc, efrom, epass, f'/static/{scac}/data/vInvoice/', dat30, invoices, packages, new_invoices, new_packages, salutation, newwb]
    etitle, ebody, emailin, emailcc, username, password, folder, dat30date, invoices, packages, ni, np, salutation, wbfile, wbattach, tone, folder2 = emaildata

    emailfrom = username

    msg = MIMEMultipart()

    msg["From"] = emailfrom
    tolist, cclist = '', ''
    emailto = []
    for emt in emailin:
        tolist = f'{tolist}, {emt}'
        emailto.append(emt)
    for emt in emailcc:
        cclist = f'{cclist}, {emt}'
        emailto.append(emt)

    from_dom = emailfrom.split('@')[1]
    #print(f'from html_mimemail in class8-utls_email: the domain is: {from_dom}')

    msg["To"] = tolist
    msg["CC"] = cclist
    msg["Subject"] = etitle
    msg['Date'] = formatdate()
    msg['Message-ID'] = make_msgid(domain=from_dom)

    #msg.add_header("Reply-To", "mnixon@firsteaglelogistics.com")

    # See if there is an attachment
    for ix, invoice in enumerate(invoices):
        if invoice is not None:
            if 'SI' in invoice: cfrom = addpath(f'static/{scac}/data/vPackage/{invoice}')
            else: cfrom = addpath(f'static/{scac}/data/vInvoice/{invoice}')
            newfile = addpath(f'static/{scac}/data/temp/{ni[ix]}')
            #print(cfrom,newfile)
            shutil.copy(cfrom,newfile)
            attachment = open(newfile, "rb")
            part = MIMEBase('application', 'octet-stream')
            part.set_payload((attachment).read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', "attachment; filename= %s" % ni[ix])
            msg.attach(part)
    for ix, package in enumerate(packages):
        if package is not None:
            cfrom = addpath(f'static/{scac}/data/vPackage/{package}')
            newfile = addpath(f'static/{scac}/data/temp/{np[ix]}')
            #print(cfrom,newfile)
            shutil.copy(cfrom,newfile)
            attachment = open(newfile, "rb")
            part = MIMEBase('application', 'octet-stream')
            part.set_payload((attachment).read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', "attachment; filename= %s" % np[ix])
            msg.attach(part)
    if wbfile is not None:
        cfrom = addpath(f'static/{scac}/data/temp/{wbfile}')
        newfile = addpath(f'static/{scac}/data/temp/{wbattach}')
        if wbfile != wbattach:  shutil.copy(cfrom, newfile)
        attachment = open(newfile, "rb")
        part = MIMEBase('application', 'octet-stream')
        part.set_payload((attachment).read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', "attachment; filename= %s" % wbattach)
        msg.attach(part)

    #attachment.close()

    msg.attach(MIMEText(ebody, 'html'))
    #msg.attach(MIMEText(signature, 'html'))
    [host, port] = ourserver.split(':')
    server = smtplib.SMTP(host, port)
    #server = smtplib.SMTP(ourserver)
    server.starttls()
    #print(f'logging in as {username} and {password}')
    code, check = server.login(username,password)
    #print('check', code, check.decode("utf-8"))
    err.append(f"Email Login: {check.decode('utf-8')}")
    err.append(f"Email To: {emailto} sent")
    err.append(f"Email From: {emailfrom}")

    server.sendmail(emailfrom, emailto, msg.as_string())

    server.quit()

    return err