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
import shutil
import os
from webapp.CCC_system_setup import addpath
from webapp.CCC_system_setup import websites, passwords, companydata, scac
from webapp.CCC_system_setup import usernames as em
import datetime
today = datetime.datetime.today()
#today = today.date()

def invoice_mimemail(docref, err):
    signature = """<html>
  <head>

    <meta http-equiv="content-type" content="text/html; charset=UTF-8">
    <title></title>
  </head>
  <body>
    <div>Support Staff<br>
    </div>
    <div>Class8 AI Software<br>
    </div>
    <div>Transportation Management Systems fused with AI<br>
    </div>
    <div>NixonAI.com<br>
    </div>
    <div><br>
    </div>
    <div><img style=""
src="data:image/png;base64,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"
        width="120" height="81"></div>
  </body>
</html>"""

    ourserver = websites['mailserver']

    emailin1=request.values.get('edat2')
    emailin2=request.values.get('edat3')
    emailcc1=request.values.get('edat4')
    emailcc2=request.values.get('edat5')
    etitle=request.values.get('edat0')
    ebody=request.values.get('edat1')
    newfile = request.values.get('edat6')

    lastpath = 'vpackages'
    if 'INV' in docref:
        lastpath = 'vinvoice'
    elif 'Proof' in docref:
        lastpath = 'vproofs'
    elif 'Manifest' in docref:
        lastpath = 'vmanifest'

    if newfile != 'none':
        cfrom = addpath(f'static/{scac}/data/{lastpath}/{docref}')
        print(cfrom,newfile)
        shutil.copy(cfrom,newfile)

    #emailto = "export@firsteaglelogistics.com"
    emailfrom = em['invo']
    username = em['invo']
    password = passwords['invo']

    msg = MIMEMultipart()
    msg["From"] = emailfrom
    msg["To"] = emailin1
    emailto=[emailin1]
    if emailin2 is not None:
        msg["To"] = emailin2
        emailto.append(emailin2)
    if emailcc1 is not None:
        msg["CC"] = emailcc1
        emailto.append(emailcc1)
    if emailcc2 is not None:
        msg["Cc"] = emailcc2
        emailto.append(emailcc2)
    msg["Subject"] = etitle

    #body = 'Dear Customer:\n\nYour invoice is attached. Please remit payment at your earliest convenience.\n\nThank you for your business- we appreciate it very much.\n\nSincerely,\n\nFIRST EAGLE LOGISTICS,INC.\n\n\nNorma Ghanem\nFirst Eagle Logistics, Inc.\n505 Hampton Park Blvd Unit O\nCapitol Heights,MD 20743\n301 516 3000'
    msg.attach(MIMEText(ebody, 'plain'))
    msg.attach(MIMEText(signature, 'html'))

    if newfile != 'none':
        attachment = open(newfile, "rb")
        part = MIMEBase('application', 'octet-stream')
        part.set_payload((attachment).read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', "attachment; filename= %s" % newfile)
        msg.attach(part)
        attachment.close()
        os.remove(newfile)



    server = smtplib.SMTP(ourserver)
    print('username=',username,password,ourserver)
    #server.connect(ourserver, 465)
    #server.ehlo()
    server.starttls()
    code, check = server.login(username,password)
    print('check', code, check.decode("utf-8"))
    err.append(f"Email Login: {check.decode('utf-8')}")
    err.append(f"Email To: {emailin1} sent")
    err.append(f"Email From: {emailfrom}")
    #emailto = []
    emailto = [emailin1]
    print('edudes', emailfrom, emailto)
    server.sendmail(emailfrom, emailto, msg.as_string())

    server.quit()



    return err
