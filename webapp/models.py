from webapp.CCC_system_setup import purpose
from datetime import datetime
from webapp import db, login_manager
from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
    return users.query.get(int(user_id))

class class8(object):
    'An Automated Workflow and Accounting Software Package for Logistics'
    version = '1.0'

def nodollar(infloat):
    outstr = "%0.2f" % infloat
    return outstr


class users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    username = db.Column(db.String(30), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    register_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    authority = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        return f"user('{self.name}','{self.username}', '{self.email}')"


class KeyInfo(db.Model):
    __tablename__ = 'keyinformation'
    id = db.Column('id', db.Integer, primary_key=True)
    Type = db.Column('Type', db.String(45))
    Name = db.Column('Name', db.String(45))
    Description = db.Column('Description', db.String(400))
    Person = db.Column('Person', db.String(45))
    Phone = db.Column('Phone', db.String(45))
    Email = db.Column('Email', db.String(45))

    def __init__(self, Type, Name, Description, Person, Phone, Email):
        self.Type = Type
        self.Name = Name
        self.Description = Description
        self.Person = Person
        self.Phone = Phone
        self.Email = Email


class ChalkBoard(db.Model):
    __tablename__ = 'chalkboard'
    id = db.Column('id', db.Integer, primary_key=True)
    Jo = db.Column('Jo', db.String(25))
    register_date = db.Column(db.DateTime)
    creator = db.Column('creator', db.String(30))
    comments = db.Column('comments', db.String(400))

    def __init__(self, Jo, register_date, creator, comments):
        self.Jo = Jo
        self.register_date = register_date
        self.creator = creator
        self.comments = comments

class IEroll(db.Model):
    __tablename__ = 'ieroll'
    id = db.Column('id', db.Integer, primary_key=True)
    Name = db.Column('Name', db.String(50))
    Category = db.Column('Category', db.String(45))
    Subcategory = db.Column('Subcategory', db.String(45))
    Type = db.Column('Type', db.String(45))
    Co = db.Column('Co', db.String(2))
    C1 = db.Column('C1', db.String(20))
    C2 = db.Column('C2', db.String(20))
    C3 = db.Column('C3', db.String(20))
    C4 = db.Column('C4', db.String(20))
    C5 = db.Column('C5', db.String(20))
    C6 = db.Column('C6', db.String(20))
    C7 = db.Column('C7', db.String(20))
    C8 = db.Column('C8', db.String(20))
    C9 = db.Column('C9', db.String(20))
    C10 = db.Column('C10', db.String(20))
    C11 = db.Column('C11', db.String(20))
    C12 = db.Column('C12', db.String(20))
    C13 = db.Column('C13', db.String(20))
    C14 = db.Column('C14', db.String(20))
    C15 = db.Column('C15', db.String(20))
    C16 = db.Column('C16', db.String(20))
    C17 = db.Column('C17', db.String(20))
    C18 = db.Column('C18', db.String(20))
    C19 = db.Column('C19', db.String(20))
    C20 = db.Column('C20', db.String(20))
    C21 = db.Column('C21', db.String(20))
    C22 = db.Column('C22', db.String(20))
    C23 = db.Column('C23', db.String(20))
    C24 = db.Column('C24', db.String(20))

    def __init__(self, Name, Category, Subcategory, Type, Co, C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12,
                 C13, C14, C15, C16, C17, C18, C19, C20, C21, C22, C23, C24):
        self.Name = Name
        self.Category = Category
        self.Subcategory = Subcategory
        self.Type = Type
        self.Co = Co
        self.C1  = C1
        self.C2  = C2
        self.C3  = C3
        self.C4  = C4
        self.C5  = C5
        self.C6  = C6
        self.C7  = C7
        self.C8  = C8
        self.C9  = C9
        self.C10  = C10
        self.C11  = C11
        self.C12  = C12
        self.C13  = C13
        self.C14  = C14
        self.C15  = C15
        self.C16  = C16
        self.C17  = C17
        self.C18  = C18
        self.C19  = C19
        self.C20  = C20
        self.C21  = C21
        self.C22  = C22
        self.C23  = C23
        self.C24  = C24

class Broll(db.Model):
    __tablename__ = 'broll'
    id = db.Column('id', db.Integer, primary_key=True)
    Name = db.Column('Name', db.String(50))
    Category = db.Column('Category', db.String(45))
    Subcategory = db.Column('Subcategory', db.String(45))
    Type = db.Column('Type', db.String(45))
    Co = db.Column('Co', db.String(2))
    Tot = db.Column('Tot', db.Integer)
    C1 = db.Column('C1', db.String(20))
    C2 = db.Column('C2', db.String(20))
    C3 = db.Column('C3', db.String(20))
    C4 = db.Column('C4', db.String(20))
    C5 = db.Column('C5', db.String(20))
    C6 = db.Column('C6', db.String(20))
    C7 = db.Column('C7', db.String(20))
    C8 = db.Column('C8', db.String(20))
    C9 = db.Column('C9', db.String(20))
    C10 = db.Column('C10', db.String(20))
    C11 = db.Column('C11', db.String(20))
    C12 = db.Column('C12', db.String(20))
    C13 = db.Column('C13', db.String(20))
    C14 = db.Column('C14', db.String(20))
    C15 = db.Column('C15', db.String(20))
    C16 = db.Column('C16', db.String(20))
    C17 = db.Column('C17', db.String(20))
    C18 = db.Column('C18', db.String(20))
    C19 = db.Column('C19', db.String(20))
    C20 = db.Column('C20', db.String(20))
    C21 = db.Column('C21', db.String(20))
    C22 = db.Column('C22', db.String(20))
    C23 = db.Column('C23', db.String(20))
    C24 = db.Column('C24', db.String(20))

    def __init__(self, Name, Category, Subcategory, Type, Co, Tot, C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12,
                 C13, C14, C15, C16, C17, C18, C19, C20, C21, C22, C23, C24):
        self.Name = Name
        self.Category = Category
        self.Subcategory = Subcategory
        self.Type = Type
        self.Co = Co
        self.Tot = Tot
        self.C1  = C1
        self.C2  = C2
        self.C3  = C3
        self.C4  = C4
        self.C5  = C5
        self.C6  = C6
        self.C7  = C7
        self.C8  = C8
        self.C9  = C9
        self.C10  = C10
        self.C11  = C11
        self.C12  = C12
        self.C13  = C13
        self.C14  = C14
        self.C15  = C15
        self.C16  = C16
        self.C17  = C17
        self.C18  = C18
        self.C19  = C19
        self.C20  = C20
        self.C21  = C21
        self.C22  = C22
        self.C23  = C23
        self.C24  = C24

class Tolls(db.Model):
    __tablename__ = 'tolls'
    id = db.Column('id', db.Integer, primary_key=True)
    Date = db.Column('Date', db.DateTime)
    Datetm = db.Column('Datetm', db.DateTime)
    Plaza = db.Column('Plaza', db.String(25))
    Amount = db.Column('Amount', db.String(25))
    Unit = db.Column('Unit', db.String(25))

    def __init__(self, Date, Datetm, Plaza, Amount, Unit):
        self.Date = Date
        self.Datetm = Datetm
        self.Plaza = Plaza
        self.Amount = Amount
        self.Unit = Unit

class Chassis(db.Model):
    __tablename__ = 'chassis'
    id = db.Column('id', db.Integer, primary_key=True)
    Jo = db.Column('Jo', db.String(20))
    Company = db.Column('Company', db.String(45))
    Date = db.Column('Date', db.DateTime)
    InvoNum = db.Column('InvoNum', db.String(20))
    Total = db.Column('Total', db.String(20))
    Container = db.Column('Container', db.String(20))
    Chass = db.Column('Chass', db.String(20))
    Amount = db.Column('Amount', db.String(20))
    Days= db.Column('Days', db.String(20))
    Dateout = db.Column('Dateout', db.String(20))
    Datein = db.Column('Datein', db.String(20))
    Booking = db.Column('Booking', db.String(20))
    Rate = db.Column('Rate', db.String(20))
    Status = db.Column('Status', db.String(20))
    Match = db.Column('Match', db.String(20))

    def __init__(self, Jo, Company, Date, InvoNum, Total, Container, Chass, Amount, Days, Dateout, Datein, Booking, Rate, Status, Match):
        self.Jo = Jo
        self.Company = Company
        self.Date = Date
        self. InvoNum = InvoNum
        self.Total = Total
        self.Container = Container
        self.Chass = Chass
        self.Amount = Amount
        self.Days = Days
        self.Dateout = Dateout
        self.Datein = Datein
        self.Booking = Booking
        self.Rate = Rate
        self.Status = Status
        self.Match = Match


class General(db.Model):
    __tablename__ = 'general'
    id = db.Column('id', db.Integer, primary_key=True)
    Subject = db.Column('Subject', db.String(50))
    Category = db.Column('Category', db.String(50))
    Textinfo = db.Column('Textinfo', db.String(400))
    Path = db.Column('Path', db.String(25))

    def __init__(self, Subject, Category, Textinfo, Path):
        self.Subject = Subject
        self.Category = Category
        self.Textinfo = Textinfo
        self.Path = Path


class Compliance(db.Model):
    __tablename__ = 'compliance'
    id = db.Column('id', db.Integer, primary_key=True)
    Subject = db.Column('Subject', db.String(45))
    Category = db.Column('Category', db.String(45))
    Item = db.Column('Item', db.String(45))
    Textinfo = db.Column('Textinfo', db.String(400))
    File1 = db.Column('File1', db.String(75))
    File2 = db.Column('File2', db.String(75))
    File3 = db.Column('File3', db.String(75))
    Date1 = db.Column('Date1', db.DateTime)
    Date2 = db.Column('Date2', db.DateTime)

    def __init__(self, Subject, Category, Item, Textinfo, File1, File2, File3, Date1, Date2):
        self.Subject = Subject
        self.Category = Category
        self.Item = Item
        self.Textinfo = Textinfo
        self.File1 = File1
        self.File2 = File2
        self.File3 = File3
        self.Date1 = Date1
        self.Date2 = Date2



class Interchange(db.Model):
    __tablename__ = 'interchange'
    id = db.Column('id', db.Integer, primary_key=True)
    Container = db.Column('Container', db.String(25))
    TruckNumber = db.Column('TruckNumber', db.String(25))
    Driver = db.Column('Driver', db.String(25))
    Chassis = db.Column('Chassis', db.String(25))
    Date = db.Column('Date', db.DateTime)
    Release = db.Column('Release', db.String(25))
    GrossWt = db.Column('GrossWt', db.String(25))
    Seals = db.Column('Seals', db.String(25))
    ConType = db.Column('ConType', db.String(25))
    CargoWt = db.Column('CargoWt', db.String(25))
    Time = db.Column('Time', db.String(25))
    Status = db.Column('Status', db.String(25))
    Source = db.Column('Source', db.String(50))
    Path = db.Column('Path', db.String(50))
    Type = db.Column('Type', db.String(25))
    Jo = db.Column('Jo', db.String(25))
    Company = db.Column('Company', db.String(50))
    Other = db.Column('Other', db.String(50))

    def __init__(self, Container, TruckNumber, Driver, Chassis, Date, Release, GrossWt, Seals, ConType, CargoWt, Time, Status, Source, Path, Type, Jo, Company, Other):
        self.Container = Container
        self.TruckNumber = TruckNumber
        self.Driver = Driver
        self.Chassis = Chassis
        self.Date = Date
        self.Release = Release
        self.GrossWt = GrossWt
        self.Seals = Seals
        self.ConType = ConType
        self.CargoWt = CargoWt
        self.Time = Time
        self.Status = Status
        self.Source = Source
        self.Path = Path
        self.Type = Type
        self.Jo = Jo
        self.Company = Company
        self.Other = Other

class StreetTurns(db.Model):
    __tablename__ = 'streetturns'
    id = db.Column('id', db.Integer, primary_key=True)
    Container = db.Column('Container', db.String(25))
    BookingTo = db.Column('BookingTo', db.String(25))
    Date = db.Column('Date', db.DateTime)
    Status = db.Column('Status', db.Integer)

    def __init__(self, Container, BookingTo, Date, Status):
        self.Container = Container
        self.BookingTo = BookingTo
        self.Date = Date
        self.Status = Status


class LastMessage(db.Model):
    __tablename__='lastmessage'
    id = db.Column('id', db.Integer, primary_key=True)
    User = db.Column('User', db.String(45))
    Err = db.Column('Err', db.String(400))

    def __init__(self, User, Err):
        self.User = User
        self.Err = Err

class QBaccounts(db.Model):
    __tablename__='qbaccounts'
    id = db.Column('id', db.Integer, primary_key=True)
    Name = db.Column('Name', db.String(99))
    Type = db.Column('Type', db.String(99))
    Sub1 = db.Column('Sub1', db.String(99))
    Sub2 = db.Column('Sub2', db.String(99))
    Co = db.Column('Co', db.String(5))

    def __init__(self, Name, Type, Sub1, Sub2, Co):
        self.Name = Name
        self.Type = Type
        self.Sub1 = Sub1
        self.Sub2 = Sub2
        self.Co = Co

class Taxmap(db.Model):
    __tablename__='taxmap'
    id = db.Column('id', db.Integer, primary_key=True)
    Name = db.Column('Name', db.String(99))
    Form = db.Column('Form', db.String(99))
    Category = db.Column('Category', db.String(99))

    def __init__(self, Name, Form, Category):
        self.Name = Name
        self.Form = Form
        self.Category = Category

class Accttypes(db.Model):
    __tablename__='accounttypes'
    id = db.Column('id', db.Integer, primary_key=True)
    Name = db.Column('Name', db.String(99))
    Taxtype = db.Column('Taxtype', db.String(99))
    Category = db.Column('Category', db.String(99))
    Subcategory = db.Column('Subcategory', db.String(99))

    def __init__(self, Name, Taxtype, Category, Subcategory):
        self.Name = Name
        self.Taxtype = Taxtype
        self.Category = Category
        self.Subcategory = Subcategory

class Focusareas(db.Model):
    __tablename__='focusareas'
    id = db.Column('id', db.Integer, primary_key=True)
    Name = db.Column('Name', db.String(45))
    Income = db.Column('Income', db.String(45))
    Expenses = db.Column('Expenses', db.String(45))
    Co = db.Column('Co', db.String(10))
    Focusid = db.Column('Focusid', db.String(10))

    def __init__(self, Name, Income, Expenses, Co, Focusid):
        self.Name = Name
        self.Income = Income
        self.Expenses = Expenses
        self.Co = Co
        self.Focusid = Focusid


class Orders(db.Model):
    __tablename__ = 'orders'
    id = db.Column('id', db.Integer, primary_key=True)
    Status = db.Column('Status', db.String(1000), default=None)
    Jo = db.Column('Jo', db.String(25), nullable=False)
    HaulType = db.Column('HaulType', db.String(50), default=None)
    Order = db.Column('Order', db.String(50), default=Jo)
    Bid = db.Column('Bid', db.Integer, default=0)
    Lid = db.Column('Lid', db.Integer, default=0)
    Did = db.Column('Did', db.Integer, default=0)
    Company = db.Column('Company', db.String(50), nullable=False)
    Location = db.Column('Location', db.String(99))
    BOL = db.Column('BOL', db.String(50), default=None)
    Booking = db.Column('Booking', db.String(50),nullable=False)
    Container = db.Column('Container', db.String(50),default=None)
    Driver = db.Column('Driver', db.String(200))
    Pickup = db.Column('Pickup', db.String(50))
    Delivery = db.Column('Delivery', db.String(50))
    Amount = db.Column('Amount', db.String(50))
    InvoTotal = db.Column('InvoTotal', db.String(45))
    Date = db.Column('Date', db.DateTime)
    Time = db.Column('Time', db.String(20))
    Date2 = db.Column('Date2', db.DateTime)
    Date3 = db.Column('Date3', db.DateTime)
    Time2 = db.Column('Time2', db.String(20))
    Time3 = db.Column('Time3', db.String(20))
    PaidInvoice = db.Column('PaidInvoice', db.String(100))
    Source = db.Column('Source', db.String(200))
    Description = db.Column('Description', db.String(400))
    Chassis = db.Column('Chassis', db.String(50))
    Detention = db.Column('Detention', db.Integer)
    Storage = db.Column('Storage', db.Integer)
    Release = db.Column('Release', db.Boolean)
    Company2 = db.Column('Company2', db.String(50))
    Location3 = db.Column('Location3', db.String(50))
    Seal = db.Column('Seal', db.String(50))
    Shipper = db.Column('Shipper', db.String(50))
    Type = db.Column('Type', db.String(50))
    Label = db.Column('Label', db.String(99))
    Dropblock1 = db.Column('Dropblock1', db.String(500))
    Dropblock2 = db.Column('Dropblock2', db.String(500))
    Dropblock3 = db.Column('Dropblock3', db.String(500))
    Commodity = db.Column('Commodity', db.String(50))
    Packing = db.Column('Packing', db.String(50))
    Links = db.Column('Links', db.String(100))
    Hstat = db.Column('Hstat', db.Integer)
    Istat = db.Column('Istat', db.Integer)
    Proof = db.Column('Proof', db.String(100))
    Invoice = db.Column('Invoice', db.String(100))
    Gate = db.Column('Gate', db.String(100))
    Package = db.Column('Package', db.String(100))
    Manifest = db.Column('Manifest', db.String(100))
    Scache = db.Column('Scache', db.Integer)
    Pcache = db.Column('Pcache', db.Integer)
    Icache = db.Column('Icache', db.Integer)
    Mcache = db.Column('Mcache', db.Integer)
    Pkcache = db.Column('Pkcache', db.Integer)
    QBi = db.Column('QBi', db.Integer)
    Truck = db.Column('Truck', db.String(45))
    PaidDate = db.Column('PaidDate', db.DateTime)
    InvoDate = db.Column('InvoDate', db.DateTime)
    PaidAmt = db.Column('PaidAmt', db.String(45))
    PayRef = db.Column('PayRef', db.String(45))
    PayMeth = db.Column('PayMeth', db.String(45))
    PayAcct = db.Column('PayAcct', db.String(45))

    def __init__(self, Status, Jo, HaulType, Order, Company, Location, BOL, Booking, Container, Driver, Pickup,
                 Delivery, Amount, Date, Time, Date2, Time2, Time3, PaidInvoice, Source, Description, Chassis,
                 Detention, Storage, Release, Company2, Seal, Shipper, Type, Bid, Lid, Did, Label, Dropblock1,
                 Dropblock2, Commodity, Packing, Links, Hstat, Istat, Proof, Invoice, Gate, Package, Manifest,
                 Scache, Pcache, Icache, Mcache, Pkcache, QBi, InvoTotal, Truck, Dropblock3, Location3, Date3,
                 InvoDate, PaidDate, PaidAmt, PayRef, PayMeth, PayAcct):
        self.Status = Status
        self.Jo = Jo
        self.HaulType = HaulType
        self.Order = Order
        self.Company = Company
        self.Location = Location
        self.BOL = BOL
        self.Booking = Booking
        self.Container = Container
        self.Driver = Driver
        self.Pickup = Pickup
        self.Delivery = Delivery
        self.Amount = Amount
        self.InvoTotal = InvoTotal
        self.Date = Date
        self.Time = Time
        self.Date2 = Date2
        self.Time2 = Time2
        self.Time3 = Time3
        self.PaidInvoice = PaidInvoice
        self.Source = Source
        self.Description = Description
        self.Chassis = Chassis
        self.Detention = Detention
        self.Storage = Storage
        self.Release = Release
        self.Company2 = Company2
        self.Seal = Seal
        self.Shipper = Shipper
        self.Type = Type
        self.Bid = Bid
        self.Lid = Lid
        self.Did = Did
        self.Label = Label
        self.Dropblock1 = Dropblock1
        self.Dropblock2 = Dropblock2
        self.Commodity = Commodity
        self.Packing = Packing
        self.Links = Links
        self.Hstat = Hstat
        self.Istat = Istat
        self.Proof = Proof
        self.Invoice = Invoice
        self.Gate = Gate
        self.Package = Package
        self.Manifest = Manifest
        self.Scache = Scache
        self.Pcache = Pcache
        self.Icache = Icache
        self.Mcache = Mcache
        self.Pkcache = Pkcache
        self.QBi = QBi
        self.Truck = Truck
        self.Dropblock3 = Dropblock3
        self.Location3 = Location3
        self.Date3 = Date3
        self.InvoDate = InvoDate
        self.PaidDate = PaidDate
        self.PaidAmt = PaidAmt
        self.PayRef = PayRef
        self.PayMeth = PayMeth
        self.PayAcct = PayAcct


class Drops(db.Model):
    __tablename__ = 'drops'
    id = db.Column('id', db.Integer, primary_key=True)
    Entity = db.Column('Entity', db.String(50))
    Addr1 = db.Column('Addr1', db.String(50))
    Addr2 = db.Column('Addr2', db.String(50))
    Phone = db.Column('Phone', db.String(50))
    Email = db.Column('Email', db.String(50))

    def __init__(self, Entity, Addr1, Addr2, Phone, Email):
        self.Entity = Entity
        self.Addr1 = Addr1
        self.Addr2 = Addr2
        self.Phone = Phone
        self.Email = Email


class JO(db.Model):
    __tablename__ = 'job'
    id = db.Column('id', db.Integer, primary_key=True)
    nextid = db.Column('nextid', db.Integer)
    jo = db.Column('jo', db.String(20))
    dinc = db.Column('dinc', db.String(50))
    dexp = db.Column('dexp', db.String(50))
    date = db.Column('date', db.DateTime)
    status = db.Column('status', db.Boolean)

    def __init__(self, nextid, jo, date, status):  # , dinc, dexp,):
        self.jo = jo
        self.nextid = nextid
        self.date = date
        self.status = status
        # self.dinc=dinc
        # self.dexp=dexp


class Services(db.Model):
    __tablename__ = 'services'
    id = db.Column('id', db.Integer, primary_key=True)
    Service = db.Column('Service', db.String(40))
    Price = db.Column('Price', db.Numeric(10, 2))

    def __init__(self, Service, Price):
        self.Service = Service
        self.Price = Price


class Gledger(db.Model):
    __tablename__ = 'gledger'
    id = db.Column('id', db.Integer, primary_key=True)
    Debit = db.Column('Debit', db.Integer)
    Credit= db.Column('Credit', db.Integer)
    Account = db.Column('Account', db.String(50))
    Aid = db.Column('Aid', db.Integer)
    Source = db.Column('Source', db.String(50))
    Sid= db.Column('Sid', db.Integer)
    Type = db.Column('Type',db.String(2))
    Tcode = db.Column('Tcode', db.String(20))
    Com = db.Column('Com',db.String(1))
    Recorded = db.Column('Recorded', db.DateTime)
    Reconciled = db.Column('Reconciled', db.Integer)
    Date = db.Column('Date', db.DateTime)
    Ref = db.Column('Ref', db.String(45))

    def __init__(self, Debit,Credit,Account,Aid,Source,Sid,Type,Tcode,Com,Recorded,Reconciled,Date,Ref):  # , dinc, dexp,):
        self.Debit=Debit
        self.Credit=Credit
        self.Account=Account
        self.Aid=Aid
        self.Source=Source
        self.Sid=Sid
        self.Type=Type
        self.Tcode=Tcode
        self.Com=Com
        self.Recorded=Recorded
        self.Reconciled=Reconciled
        self.Date = Date
        self.Ref = Ref

class Divisions(db.Model):
    __tablename__ = 'divisions'
    id = db.Column('id', db.Integer, primary_key=True)
    Name = db.Column('Name', db.String(45))
    Co = db.Column('Co', db.String(45))
    Color = db.Column('Color', db.String(45))
    Apportion = db.Column('Apportion', db.String(45))


    def __init__(self, Name, Co, Color, Apportion):
        self.Name = Name
        self.Co = Co
        self.Color = Color
        self.Apportion = Apportion


class Quotes(db.Model):
    __tablename__ = 'quotes'
    id = db.Column('id', db.Integer, primary_key=True)
    Date = db.Column('Date', db.DateTime)
    From = db.Column('From', db.String(200))
    Subject = db.Column('Subject', db.String(200))
    Body = db.Column('Body', db.String(500))
    Mid = db.Column('Mid', db.String(200))
    Person = db.Column('Person', db.String(100))
    Response = db.Column('Response', db.String(500))
    Amount = db.Column('Amount', db.String(45))
    Location = db.Column('Location', db.String(200))
    Status = db.Column('Status', db.Integer)
    Responder = db.Column('Responder', db.String(45))
    RespDate = db.Column('RespDate', db.DateTime)
    Start = db.Column('Start', db.String(45))

    def __init__(self, Date, From, Subject, Body, Response, Amount, Location, Status, Responder, RespDate, Start, Mid, Person):
        self.Date = Date
        self.From = From
        self.Subject = Subject
        self.Body = Body
        self.Response = Response
        self.Amount = Amount
        self.Location = Location
        self.Status = Status
        self.Responder = Responder
        self.RespDate = RespDate
        self.Start = Start
        self.Mid = Mid
        self.Person = Person


class DriverAssign(db.Model):
    __tablename__ = 'driverassign'
    id = db.Column('id', db.Integer, primary_key=True)
    Date = db.Column('Date', db.DateTime)
    Driver = db.Column('Driver', db.String(30))
    UnitStart = db.Column('UnitStart', db.String(20))
    UnitStop = db.Column('UnitStop', db.String(20))
    StartStamp = db.Column('StartStamp', db.DateTime)
    EndStamp = db.Column('EndStamp', db.DateTime)
    Hours = db.Column('Hours', db.String(45))
    Miles = db.Column('Miles', db.String(45))
    Status = db.Column('Status', db.String(45))
    Radius = db.Column('Radius', db.String(45))
    Rloc = db.Column('Rloc', db.String(200))

    def __init__(self, Date, Driver, UnitStart, UnitStop,StartStamp,EndStamp,Hours,Miles,Status,Radius,Rloc):
        self.Date = Date
        self.Driver = Driver
        self.UnitStart = UnitStart
        self.UnitStop = UnitStop
        self.StartStamp = StartStamp
        self.EndStamp = EndStamp
        self.Hours = Hours
        self.Miles = Miles
        self.Status = Status
        self.Radius = Radius
        self.Rloc = Rloc


class People(db.Model):
    __tablename__ = 'people'
    id = db.Column('id', db.Integer, primary_key=True)
    Ptype = db.Column('Ptype', db.String(25))
    Company = db.Column('Company', db.String(50))
    First = db.Column('First', db.String(25))
    Middle = db.Column('Middle', db.String(25))
    Last = db.Column('Last', db.String(25))
    Addr1 = db.Column('Addr1', db.String(75))
    Addr2 = db.Column('Addr2', db.String(50))
    Addr3 = db.Column('Addr3', db.String(50))
    Idtype = db.Column('Idtype', db.String(25))
    Idnumber = db.Column('Idnumber', db.String(25))
    Telephone = db.Column('Telephone', db.String(75))
    Email = db.Column('Email', db.String(50))
    Associate1 = db.Column('Associate1', db.String(50))
    Associate2 = db.Column('Associate2', db.String(50))
    Temp1 = db.Column('Temp1', db.String(200))
    Temp2 = db.Column('Temp2', db.String(200))
    Date1 = db.Column('Date1', db.DateTime)
    Date2 = db.Column('Date2', db.DateTime)
    Source = db.Column('Source', db.String(200))
    Accountid = db.Column('Accountid', db.Integer)

    def __init__(self, Ptype, Company, First, Middle, Last, Addr1, Addr2, Addr3, Idtype, Idnumber, Telephone, Email, Associate1, Associate2, Temp1, Temp2, Date1, Date2, Source, Accountid):
        self.Ptype = Ptype
        self.Company = Company
        self.First = First
        self.Middle = Middle
        self.Last = Last
        self.Addr1 = Addr1
        self.Addr2 = Addr2
        self.Addr3 = Addr3
        self.Idtype = Idtype
        self.Idnumber = Idnumber
        self.Telephone = Telephone
        self.Email = Email
        self.Associate1 = Associate1
        self.Associate2 = Associate2
        self.Temp1 = Temp1
        self.Temp2 = Temp2
        self.Date1 = Date1
        self.Date2 = Date2
        self.Source = Source
        self.Accountid = Accountid



class Dealer(db.Model):
    __tablename__ = 'dealer'
    id = db.Column('id', db.Integer, primary_key=True)
    Jo = db.Column('Jo', db.String(25))
    Pid = db.Column('Pid', db.Integer)
    Company = db.Column('Company', db.String(50))
    Aid = db.Column('Aid', db.Integer)
    Make = db.Column('Make', db.String(25))
    Model = db.Column('Model', db.String(25))
    Year = db.Column('Year', db.String(25))
    Vin = db.Column('Vin', db.String(25))
    Cost = db.Column('Cost', db.String(25))
    Sale = db.Column('Sale', db.String(25))
    Bfee = db.Column('Bfee', db.String(25))
    Tow = db.Column('Tow', db.String(25))
    Repair = db.Column('Repair', db.String(25))
    Oitem = db.Column('Oitem', db.String(25))
    Ocost = db.Column('Ocost', db.String(25))
    Ipath = db.Column('Ipath', db.String(50))
    Apath = db.Column('Apath', db.String(50))
    Cache = db.Column('Cache', db.Integer)
    Status = db.Column('Status', db.String(25))
    Label = db.Column('Label', db.String(99))
    Date = db.Column('Date', db.DateTime)
    DocumentFee = db.Column('DocumentFee', db.String(25))

    def __init__(self, Jo, Pid, Company, Aid, Make, Model, Year, Vin, Cost, Sale, Bfee, DocumentFee, Tow, Repair,
                 Oitem, Ocost, Ipath, Apath, Cache, Status, Label, Date):
        self.Jo = Jo
        self.Pid = Pid
        self.Company = Company
        self.Aid = Aid
        self.Make = Make
        self.Model = Model
        self.Year = Year
        self.Vin = Vin
        self.Cost = Cost
        self.Sale = Sale
        self.Bfee = Bfee
        self.DocumentFee = DocumentFee
        self.Tow = Tow
        self.Repair = Repair
        self.Oitem = Oitem
        self.Ocost = Ocost
        self.Ipath = Ipath
        self.Apath = Apath
        self.Cache = Cache
        self.Status = Status
        self.Label = Label
        self.Date = Date


class OverSeas(db.Model):
    __tablename__ = 'overseas'
    id = db.Column('id', db.Integer, primary_key=True)
    Jo = db.Column('JO', db.String(25))
    Pid = db.Column('Pid', db.Integer)
    MoveType = db.Column('MoveType', db.String(25))
    Direction = db.Column('Direction', db.String(25))
    Commodity = db.Column('Commodity', db.String(25))
    Pod = db.Column('Pod', db.String(50))
    Pol = db.Column('Pol', db.String(25))
    Origin = db.Column('Origin', db.String(25))
    PuDate = db.Column('PuDate', db.DateTime)
    RetDate = db.Column('RetDate', db.DateTime)
    Tpath = db.Column('Tpath', db.String(25))
    ContainerType = db.Column('ContainerType', db.String(25))
    Container = db.Column('Container', db.String(25))
    Booking = db.Column('Booking', db.String(25))
    CommoList = db.Column('CommoList', db.Integer)
    ExportID = db.Column('ExportID', db.Integer)
    ConsigID = db.Column('ConsigID', db.Integer)
    NotifyID = db.Column('NotifyID', db.Integer)
    FrForID = db.Column('FrForID', db.Integer)
    PreCarryID = db.Column('PreCarryID', db.Integer)
    BillTo = db.Column('BillTo', db.String(50))
    Exporter = db.Column('Exporter', db.String(50))
    Consignee = db.Column('Consignee', db.String(50))
    Notify = db.Column('Notify', db.String(50))
    FrFor = db.Column('FrFor', db.String(50))
    PreCarry = db.Column('PreCarry', db.String(50))
    Estimate = db.Column('Estimate', db.String(25))
    Charge = db.Column('Charge', db.String(25))
    Itotal = db.Column('Itotal', db.String(25))
    Dpath = db.Column('Dpath', db.String(50))
    Ipath = db.Column('Ipath', db.String(50))
    Apath = db.Column('Apath', db.String(50))
    Cache = db.Column('Cache', db.Integer)
    Status = db.Column('Status', db.String(25))
    Label = db.Column('Label', db.String(99))
    Driver = db.Column('Driver', db.String(50))
    Seal = db.Column('Seal', db.String(25))
    Description = db.Column('Description', db.String(400))
    RelType = db.Column('RelType', db.String(25))
    AES = db.Column('AES', db.String(50))
    ExpRef = db.Column('ExpRef', db.String(45))
    AddNote = db.Column('AddNote', db.String(45))

    def __init__(self, Jo, Pid, MoveType, Direction, Commodity, Pod, Pol, Origin, ContainerType, Container, Booking, CommoList, ExportID, ConsigID, NotifyID, FrForID, PreCarryID, BillTo, Exporter, Consignee, Notify, FrFor, PreCarry, Estimate, Charge, Dpath, Ipath, Apath, Cache, Status, Label, Driver, Seal, Description, Tpath, PuDate, RetDate, Itotal, RelType, AES, ExpRef, AddNote):
        self.Jo = Jo
        self.Pid = Pid
        self.MoveType = MoveType
        self.Direction = Direction
        self.Commodity = Commodity
        self.Pod = Pod
        self.Pol = Pol
        self.Origin = Origin
        self.PuDate = PuDate
        self.RetDate = RetDate
        self.Tpath = Tpath
        self.Itotal = Itotal
        self.ContainerType = ContainerType
        self.Container = Container
        self.Booking = Booking
        self.CommoList = CommoList
        self.ExportID = ExportID
        self.ConsigID = ConsigID
        self.NotifyID = NotifyID
        self.FrForID = FrForID
        self.PreCarryID = PreCarryID
        self.BillTo = BillTo
        self.Exporter = Exporter
        self.Consignee = Consignee
        self.Notify = Notify
        self.FrFor = FrFor
        self.PreCarry = PreCarry
        self.Estimate = Estimate
        self.Charge = Charge
        self.Dpath = Dpath
        self.Ipath = Ipath
        self.Apath = Apath
        self.Cache = Cache
        self.Status = Status
        self.Label = Label
        self.Driver = Driver
        self.Seal = Seal
        self.Description = Description
        self.RelType = RelType
        self.AES = AES
        self.ExpRef = ExpRef
        self.AddNote = AddNote


class Autos(db.Model):
    __tablename__ = 'autos'
    id = db.Column('id', db.Integer, primary_key=True)
    Jo = db.Column('JO', db.String(25))
    Year = db.Column('Year', db.String(25))
    Make = db.Column('Make', db.String(25))
    Model = db.Column('Model', db.String(25))
    Color = db.Column('Color', db.String(25))
    VIN = db.Column('VIN', db.String(25))
    Title = db.Column('Title', db.String(25))
    State = db.Column('State', db.String(25))
    EmpWeight = db.Column('EmpWeight', db.String(25))
    Value = db.Column('Value', db.String(50))
    TowCompany = db.Column('TowCompany', db.String(50))
    TowCost = db.Column('TowCost', db.String(25))
    TowCostEa = db.Column('TowCostEa', db.String(25))
    Status = db.Column('Status', db.String(25))
    Date = db.Column('Date', db.DateTime)
    Date2 = db.Column('Date2', db.DateTime)
    Pufrom = db.Column('Pufrom', db.String(50))
    Delto = db.Column('Delto', db.String(50))
    Ncars = db.Column('Ncars', db.Integer)
    Orderid = db.Column('Orderid', db.String(25))
    Hjo = db.Column('Hjo', db.String(25))
    Pid = db.Column('Pid', db.Integer)
    Customer = db.Column('Customer', db.String(50))
    Cost = db.Column('Cost', db.String(25))
    Sale = db.Column('Sale', db.String(25))
    Bfee = db.Column('Bfee', db.String(25))
    Source = db.Column('Source', db.String(50))
    Proof = db.Column('Proof', db.String(50))
    TitleDoc = db.Column('TitleDoc', db.String(50))
    Invoice= db.Column('Invoice', db.String(50))
    Package= db.Column('Package', db.String(50))
    Scache = db.Column('Scache', db.Integer)
    Pcache = db.Column('Pcache', db.Integer)
    Icache = db.Column('Icache', db.Integer)
    Tcache = db.Column('Tcache', db.Integer)
    Pkcache = db.Column('Pkcache', db.Integer)

    def __init__(self, Jo, Year, Make, Model, Color, VIN, Title, State, EmpWeight, Value, TowCompany,
                 TowCost, TowCostEa, Status, Date, Date2, Pufrom, Delto, Ncars, Orderid, Hjo, Pid, Customer,
                 Cost, Sale, Bfee, Source, Proof, TitleDoc, Invoice, Package, Scache, Pcache, Icache, Tcache, Pkcache):
        self.Jo = Jo
        self.Year = Year
        self.Make = Make
        self.Model = Model
        self.Color = Color
        self.VIN = VIN
        self.Title = Title
        self.State = State
        self.EmpWeight = EmpWeight
        self.Value = Value
        self.TowCompany = TowCompany
        self.TowCost = TowCost
        self.TowCostEa = TowCostEa
        self.Status = Status
        self.Date = Date
        self.Date2 = Date2
        self.Pufrom = Pufrom
        self.Delto = Delto
        self.Ncars = Ncars
        self.Orderid = Orderid
        self.Hjo = Hjo
        self.DelTicket = DelTicket
        self.TitlePdf = TitlePdf
        self.Pid = Pid
        self.Customer = Customer
        self.Cost = Cost
        self.Sale = Sale
        self.Bfee = Bfee
        self.Source = Source
        self.Proof = Proof
        self.TitleDoc = TitleDoc
        self.Invoice = Invoice
        self.Package = Package
        self.Scache = Scache
        self.Pcache = Pcache
        self.Tcache = Tcache
        self.Icache = Icache
        self.Pkcache = Pkcache



class Bookings(db.Model):
    __tablename__ = 'bookings'
    id = db.Column('id', db.Integer, primary_key=True)
    Jo = db.Column('JO', db.String(25))
    Booking = db.Column('Booking', db.String(25))
    ExportRef = db.Column('ExportRef', db.String(25))
    Vessel = db.Column('Vessel', db.String(50))
    Line = db.Column('Line', db.String(50))
    PortCut = db.Column('PortCut', db.DateTime)
    DocCut = db.Column('DocCut', db.DateTime)
    SailDate = db.Column('SailDate', db.DateTime)
    EstArr = db.Column('EstArr', db.DateTime)
    RelType = db.Column('RelType', db.String(25))
    AES = db.Column('AES', db.String(50))
    Original = db.Column('Original', db.String(50))
    Amount = db.Column('Amount', db.String(25))
    LoadPort = db.Column('LoadPort', db.String(50))
    Dest = db.Column('Dest', db.String(50))
    Status = db.Column('Status', db.String(25))

    def __init__(self, Jo, Booking, ExportRef, Vessel, Line, PortCut, DocCut, SailDate, EstArr, RelType,
                 AES, Original, Amount, LoadPort, Dest, Status):
        self.Jo = Jo
        self.Booking = Booking
        self.ExportRef = ExportRef
        self.Vessel = Vessel
        self.Line = Line
        self.PortCut = PortCut
        self.DocCut = DocCut
        self.SailDate = SailDate
        self.EstArr = EstArr
        self.RelType = RelType
        self.AES = AES
        self.Original = Original
        self.Amount = Amount
        self.LoadPort = LoadPort
        self.Dest = Dest
        self.Status = Status


class Vehicles(db.Model):
    __tablename__ = 'vehicles'
    id = db.Column('id', db.Integer, primary_key=True)
    Unit = db.Column('Unit', db.String(9))
    Year = db.Column('Year', db.String(25))
    Make = db.Column('Make', db.String(25))
    Model = db.Column('Model', db.String(25))
    Color = db.Column('Color', db.String(25))
    VIN = db.Column('VIN', db.String(25))
    Title = db.Column('Title', db.String(25))
    Plate = db.Column('Plate', db.String(25))
    EmpWeight = db.Column('EmpWeight', db.String(25))
    GrossWt = db.Column('GrossWt', db.String(25))
    DOTNum = db.Column('DOTNum', db.String(25))
    ExpDate = db.Column('ExpDate', db.Date)
    Odometer = db.Column('Odometer', db.String(25))
    Owner = db.Column('Owner', db.String(50))
    Status = db.Column('Status', db.String(25))
    Ezpassxponder = db.Column('Ezpassxponder', db.String(45))
    Portxponder = db.Column('Portxponder', db.String(45))
    ServStr = db.Column('StartedService', db.Date)
    ServStp = db.Column('StoppedService', db.Date)
    Active = db.Column('Active', db.Integer)

    def __init__(self, Unit, Year, Make, Model, Color, VIN, Title, Plate, EmpWeight, GrossWt, DOTNum, ExpDate, Odometer, Owner, Status, Ezpassxponder, Portxponder, ServStr, ServStp, Active):
        self.Unit = Unit
        self.Year = Year
        self.Make = Make
        self.Model = Model
        self.Color = Color
        self.VIN = VIN
        self.Title = Title
        self.Plate = Plate
        self.EmpWeight = EmpWeight
        self.GrossWt = GrossWt
        self.DOTNum = DOTNum
        self.ExpDate = ExpDate
        self.Owner = Owner
        self.Odometer = Odometer
        self.Status = Status
        self.Ezpassxponder = Ezpassxponder
        self.Portxponder = Portxponder
        self.ServStr = ServStr
        self.ServStp = ServStp
        self.Active = Active

class Trucklog(db.Model):
    __tablename__ = 'trucklog'
    id = db.Column('id', db.Integer, primary_key=True)
    Date = db.Column('Date', db.Date)
    Tag = db.Column('Tag', db.String(45))
    Unit = db.Column('Unit', db.String(45))
    GPSin= db.Column('GPSin', db.DateTime)
    GPSout = db.Column('GPSout', db.DateTime)
    Shift = db.Column('Shift', db.String(45))
    Distance = db.Column('Distance', db.String(45))
    Rdist = db.Column('Rdist', db.String(45))
    Rloc = db.Column('Rloc', db.String(200))
    Gotime = db.Column('Gotime', db.String(45))
    Odomstart = db.Column('Odomstart', db.String(45))
    Odomstop = db.Column('Odomstop', db.String(45))
    Odverify = db.Column('Odverify', db.String(45))
    DriverStart = db.Column('DriverStart', db.String(45))
    DriverEnd = db.Column('DriverEnd', db.String(45))
    Maintrecord = db.Column('Maintrecord', db.String(45))
    Locationstart = db.Column('Locationstart', db.String(200))
    Locationstop = db.Column('Locationstop', db.String(200))
    Maintid = db.Column('Maintid', db.String(45))
    Status = db.Column('Status', db.String(45))

    def __init__(self, Date, Tag, Unit, GPSin, GPSout, Shift, Distance, Gotime, Odomstart, Odomstop, Odverify, DriverStart, DriverEnd, Maintrecord, Locationstart, Locationstop, Maintid, Status, Rdist, Rloc):
        self.Date = Date
        self.GPSin = GPSin
        self.GPSout = GPSout
        self.Tag = Tag
        self.Unit = Unit
        self.Distance = Distance
        self.Shift = Shift
        self.Gotime = Gotime
        self.Odomstart = Odomstart
        self.Odomstop = Odomstop
        self.Odverify = Odverify
        self.DriverStart = DriverStart
        self.DriverEnd = DriverEnd
        self.Maintrecord = Maintrecord
        self.Locationstart = Locationstart
        self.Locationstop = Locationstop
        self.Mainid = Maintid
        self.Status = Status
        self.Rdist = Rdist
        self.Rloc = Rloc


class Invoices(db.Model):
    __tablename__ = 'invoices'
    id = db.Column('id', db.Integer, primary_key=True)
    Jo = db.Column('Jo', db.String(25))
    SubJo = db.Column('SubJo', db.String(25))
    Pid = db.Column('Pid', db.Integer)
    Service = db.Column('Service', db.String(50))
    Description = db.Column('Description', db.String(400))
    Ea = db.Column('Ea', db.Numeric(10, 2))
    Qty = db.Column('Qty', db.Numeric(10, 2))
    Amount = db.Column('Amount', db.Numeric(10, 2))
    Total = db.Column('Total', db.Numeric(10, 2))
    Date = db.Column('Date', db.DateTime)
    Original = db.Column('Original', db.String(50))
    Status = db.Column('Status', db.String(25))

    def __init__(self, Jo, SubJo, Pid, Service, Description, Ea, Qty, Amount, Total, Date, Original, Status):
        self.Jo = Jo
        self.SubJo = SubJo
        self.Pid = Pid
        self.Service = Service
        self.Description = Description
        self.Ea = Ea
        self.Qty = Qty
        self.Amount = Amount
        self.Total = Total
        self.Date = Date
        self.Original = Original
        self.Status = Status

class SumInv(db.Model):
    __tablename__ = 'suminv'
    id = db.Column('id', db.Integer, primary_key=True)
    Si = db.Column('Si', db.String(25))
    Jo = db.Column('Jo', db.String(25))
    Begin = db.Column('Begin', db.DateTime)
    End = db.Column('End', db.DateTime)
    Release = db.Column('Release', db.String(45))
    Container = db.Column('Container', db.String(45))
    Type = db.Column('Type', db.String(45))
    Description = db.Column('Description', db.String(300))
    Amount = db.Column('Amount',  db.String(45))
    Total = db.Column('Total',  db.String(45))
    Source = db.Column('Source', db.String(50))
    Status = db.Column('Status', db.String(25))
    Cache = db.Column('Cache', db.Integer)
    Pid = db.Column('Pid', db.Integer)
    Billto = db.Column('Billto', db.String(50))
    InvoDate = db.Column('InvoDate', db.DateTime)

    def __init__(self, Si, Jo, Begin, End, Release, Container, Type, Description, Amount, Source, Status, Cache, Pid, Total, Billto, InvoDate):
        self.Jo = Jo
        self.Si = Si
        self.Begin = Begin
        self.End = End
        self.Release = Release
        self.Container = Container
        self.Type = Type
        self.Source = Source
        self.Description = Description
        self.Amount = Amount
        self.Total = Total
        self.Status = Status
        self.Cache = Cache
        self.Pid = Pid
        self.Billto = Billto
        self.InvoDate = InvoDate


class Income(db.Model):
    __tablename__ = 'income'
    id = db.Column('id', db.Integer, primary_key=True)
    Jo = db.Column('Jo', db.String(25))
    Account = db.Column('Account', db.String(99))
    Pid = db.Column('Pid', db.Integer)
    Description = db.Column('Description', db.String(200))
    Amount = db.Column('Amount', db.String(45))
    Ref = db.Column('Ref', db.String(25))
    Date = db.Column('Date', db.DateTime)
    Original = db.Column('Original', db.String(99))
    From = db.Column('From', db.String(45))
    Bank = db.Column('Bank', db.String(45))
    Date2 = db.Column('Date2', db.DateTime)
    Depositnum = db.Column('Depositnum', db.String(45))

    def __init__(self, Jo, Account, Pid, Description, Amount, Ref, Date, Original, From, Bank, Date2, Depositnum):
        self.Jo = Jo
        self.Account = Account
        self.Pid = Pid
        self.Description = Description
        self.Amount = Amount
        self.Ref = Ref
        self.Date = Date
        self.Original = Original
        self.From = From
        self.Bank = Bank
        self.Date2 = Date2
        self.Depositnum = Depositnum

class Deposits(db.Model):
    __tablename__ = 'deposits'
    id = db.Column('id', db.Integer, primary_key=True)
    Jo = db.Column('Jo', db.String(25))
    Account = db.Column('Account', db.String(99))
    Pid = db.Column('Pid', db.Integer)
    Total = db.Column('Total', db.String(25))
    Amount = db.Column('Amount', db.String(25))
    Ref = db.Column('Ref', db.String(25))
    Date = db.Column('Date', db.DateTime)
    Original = db.Column('Original', db.String(99))
    From = db.Column('From', db.String(45))
    Bank = db.Column('Bank', db.String(45))
    Date2 = db.Column('Date2', db.DateTime)
    Depositnum = db.Column('Depositnum', db.String(45))

    def __init__(self, Jo, Account, Pid, Total, Amount, Ref, Date, Original, From, Bank, Date2, Depositnum):
        self.Jo = Jo
        self.Account = Account
        self.Pid = Pid
        self.Total = Total
        self.Amount = Amount
        self.Ref = Ref
        self.Date = Date
        self.Original = Original
        self.From = From
        self.Bank = Bank
        self.Date2 = Date2
        self.Depositnum = Depositnum

class Reconciliations(db.Model):
    __tablename__ = 'reconciliations'
    id = db.Column('id', db.Integer, primary_key=True)
    Account = db.Column('Account', db.String(45))
    Rdate = db.Column('Rdate', db.DateTime)
    Bbal = db.Column('Bbal', db.String(45))
    Ebal = db.Column('Ebal', db.String(45))
    Deposits = db.Column('Deposits', db.String(45))
    Withdraws = db.Column('Withdraws', db.String(45))
    Servicefees = db.Column('Servicefees', db.String(45))
    DepositList = db.Column('DepositList', db.String(300))
    WithdrawList = db.Column('WithdrawList', db.String(300))
    Status = db.Column('Status', db.Integer)
    Diff = db.Column('Diff', db.String(45))

    def __init__(self, Account, Rdate, Bbal, Ebal, Deposits, Withdraws, Servicefees, DepositList, WithdrawList, Status, Diff):
        self.Account = Account
        self.Rdate = Rdate
        self.Bbal = Bbal
        self.Ebal = Ebal
        self.Deposits = Deposits
        self.Withdraws = Withdraws
        self.Servicefees = Servicefees
        self.DepositList = DepositList
        self.WithdrawList = WithdrawList
        self.Status = Status
        self.Diff = Diff

class Adjusting(db.Model):
    __tablename__ = 'adjusting'
    id = db.Column('id', db.Integer, primary_key=True)
    Jo = db.Column('Jo', db.String(45))
    Date = db.Column('Date', db.DateTime)
    DateEnd = db.Column('DateEnd', db.DateTime)
    Mop = db.Column('Mop', db.Integer)
    Moa = db.Column('Moa', db.Integer)
    Asset = db.Column('Asset', db.String(45))
    Expense = db.Column('Expense', db.String(45))
    Amtp = db.Column('Amtp', db.String(45))
    Amta= db.Column('Amta', db.String(45))
    Status = db.Column('Status', db.Integer)

    def __init__(self, Jo, Date, Mop, Moa, Asset, Expense, Amtp, Amta, Status, DateEnd):
        self.Jo = Jo
        self.Date = Date
        self. Mop = Mop
        self. Moa = Moa
        self.Asset = Asset
        self.Expense = Expense
        self.Amtp = Amtp
        self.Amta = Amta
        self.Status = Status
        self.DateEnd = DateEnd

class Bills(db.Model):
    __tablename__ = 'bills'
    id = db.Column('id', db.Integer, primary_key=True)
    Jo = db.Column('Jo', db.String(25))
    Pid = db.Column('Pid', db.Integer)
    Company = db.Column('Company', db.String(50))
    Memo = db.Column('Memo', db.String(50))
    Description = db.Column('Description', db.String(600))
    bAmount = db.Column('bAmount', db.String(20))
    Status = db.Column('Status', db.String(25))
    Cache = db.Column('Cache', db.Integer)
    Original = db.Column('Original', db.String(75))
    Ref = db.Column('Ref', db.String(50))
    bDate = db.Column('bDate', db.DateTime)
    pDate = db.Column('pDate', db.DateTime)
    pAmount = db.Column('pAmount', db.String(20))
    pMulti = db.Column('pMulti', db.String(20))
    pAccount = db.Column('Account', db.String(50))
    bAccount = db.Column('bAccount', db.String(50))
    bType = db.Column('bType', db.String(25))
    bCat = db.Column('bCat', db.String(45))
    bSubcat = db.Column('bSubcat', db.String(45))
    Link = db.Column('Link', db.String(100))
    User = db.Column('User', db.String(25))
    Co = db.Column('Co', db.String(9))
    Temp1 = db.Column('Temp1', db.String(50))
    Temp2 = db.Column('Temp2', db.String(200))
    Recurring = db.Column('Recurring', db.Integer)
    dDate = db.Column('dDate', db.DateTime)
    pAmount2 = db.Column('pAmount2', db.String(20))
    pDate2 = db.Column('pDate2', db.DateTime)
    Code1 = db.Column('Code1', db.String(45))
    Code2 = db.Column('Code2', db.String(45))
    CkCache = db.Column('CkCache', db.Integer)
    QBi = db.Column('QBi', db.Integer)
    iflag = db.Column('iflag', db.Integer)
    PmtList= db.Column('PmtList', db.String(200))
    PacctList = db.Column('PacctList', db.String(200))
    RefList = db.Column('RefList', db.String(200))
    MemoList = db.Column('MemoList', db.String(200))
    PdateList = db.Column('PdateList', db.String(200))
    CheckList = db.Column('CheckList', db.String(200))
    MethList = db.Column('MethList', db.String(200))

    def __init__(self, Jo, Pid, Company, Memo, Description, bAmount, Status, Cache, Original, Ref, bDate, pDate, pAmount, pMulti, pAccount, bAccount, bType, bCat, bSubcat, Link, User, Co, Temp1, Temp2, Recurring, dDate, pAmount2, pDate2, Code1, Code2, CkCache, QBi, iflag, PmtList, PacctList, RefList, MemoList, PdateList, CheckList, MethList):
        self.Jo = Jo
        self.Pid = Pid
        self.Company = Company
        self.Memo = Memo
        self.Description = Description
        self.bAmount = bAmount
        self.Status = Status
        self.Cache = Cache
        self.Original = Original
        self.Ref = Ref
        self.bDate = bDate
        self.pDate = pDate
        self.pAmount = pAmount
        self.pMulti = pMulti
        self.pAccount = pAccount
        self.bAccount = bAccount
        self.bType = bType
        self.bCat = bCat
        self.bSubcat = bSubcat
        self.Link = Link
        self.User = User
        self.Co = Co
        self.Temp1 = Temp1
        self.Temp2 = Temp2
        self.Recurring = Recurring
        self.dDate = dDate
        self.pAmount2 = pAmount2
        self.pDate2 = pDate2
        self.Code1 = Code1
        self.Code2 = Code2
        self.CkCache = CkCache
        self.QBi = QBi
        self.iflag = iflag
        self.PmtList = PmtList
        self.PacctList = PacctList
        self.RefList = RefList
        self.MemoList = MemoList
        self.PdateList = PdateList
        self.CheckList = CheckList
        self.MethList = MethList

    def Bal(self):
        try:
            paid = float(self.pAmount)
        except:
            paid = 0.00
        try:
            owe = float(self.bAmount)
        except:
            owe = 0.00
        return nodollar(owe-paid)



class Accounts(db.Model):
    __tablename__ = 'accounts'
    id = db.Column('id', db.Integer, primary_key=True)
    Name = db.Column('Name', db.String(50))
    Balance = db.Column('Balance', db.String(25))
    AcctNumber = db.Column('AcctNumber', db.String(25))
    Routing = db.Column('Routing', db.String(25))
    Payee = db.Column('Payee', db.String(50))
    Type = db.Column('Type', db.String(45))
    Description = db.Column('Description', db.String(100))
    Category = db.Column('Category', db.String(45))
    Subcategory = db.Column('Subcategory', db.String(45))
    Taxrollup = db.Column('Taxrollup', db.String(200))
    Co = db.Column('Co', db.String(2))
    QBmap = db.Column('QBmap', db.String(200))
    Shared = db.Column('Shared', db.String(200))

    def __init__(self, Name, Balance, AcctNumber, Routing, Payee, Type, Description, Category, Subcategory, Taxrollup, Co, QBmap, Shared):
        self.Name = Name
        self.Balance = Balance
        self.AcctNumber = AcctNumber
        self.Routing = Routing
        self.Payee = Payee
        self.Type = Type
        self.Description = Description
        self.Category = Category
        self.Subcategory = Subcategory
        self.Taxrollup = Taxrollup
        self.Co = Co
        self.QBmap = QBmap
        self.Shared = Shared
        
 
class Portlog(db.Model):
    __tablename__ = 'portlog'
    id = db.Column('id', db.Integer, primary_key=True)
    Date = db.Column('Date', db.Date)
    Unit = db.Column('Unit', db.String(45))
    Driver = db.Column('Driver', db.String(45))
    GPSin= db.Column('GPSin', db.DateTime)
    GPSout = db.Column('GPSout', db.DateTime)
    PortTime = db.Column('PortTime', db.String(45))
    CustTime = db.Column('CustTime', db.String(45))
    ConIn = db.Column('ConIn', db.String(45))
    ConOut = db.Column('ConOut', db.String(45))
    Status = db.Column('Status', db.String(45))
    Portmiles = db.Column('Portmiles', db.String(45))

    def __init__(self, Date, Unit, Driver, GPSin, GPSout, PortTime, CustTime, ConIn, ConOut, Status, Portmiles):
        self.Date = Date
        self.GPSin = GPSin
        self.GPSout = GPSout
        self.Unit = Unit
        self.Driver = Driver
        self.PortTime = PortTime
        self.CustTime = CustTime
        self.ConIn = ConIn
        self.ConOut = ConOut
        self.Status = Status
        self.Portmiles = Portmiles
        
class Driverlog(db.Model):
    __tablename__ = 'driverlog'
    id = db.Column('id', db.Integer, primary_key=True)
    Date = db.Column('Date', db.Date)
    Driver = db.Column('Driver', db.String(45))
    GPSin= db.Column('GPSin', db.DateTime)
    GPSout = db.Column('GPSout', db.DateTime)
    Odomstart = db.Column('Odomstart', db.String(45))
    Odomstop = db.Column('Odomstop', db.String(45))
    Truck = db.Column('Truck', db.String(45))
    Locationstart = db.Column('Locationstart', db.String(45))
    Locationstop = db.Column('Locationstop', db.String(45))
    Shift = db.Column('Shift', db.String(45))
    Status = db.Column('Status', db.String(45))

    def __init__(self, Date, Driver, GPSin, GPSout, Odomstart, Odomstop, Truck, Locationstart, Locationstop, Shift, Status):
        self.Date = Date
        self.GPSin = GPSin
        self.GPSout = GPSout
        self.Odomstart = Odomstart
        self.Odomstop = Odomstop
        self.Truck = Truck
        self.Driver = Driver
        self.Locationstart = Locationstart
        self.Locationstop = Locationstop
        self.Shift = Shift
        self.Status = Status
        
class Drivers(db.Model):
    __tablename__ = 'drivers'
    id = db.Column('id', db.Integer, primary_key=True)
    Name = db.Column('Name', db.String(50))
    Addr1= db.Column('Addr1', db.String(45))
    Addr2= db.Column('Addr2', db.String(45))
    Phone = db.Column('Phone', db.String(25))
    Email = db.Column('Email', db.String(50))
    Truck = db.Column('Truck', db.String(9))
    Tag = db.Column('Tag', db.String(9))
    ScanCDL = db.Column('ScanCDL', db.String(50))
    ScanMed = db.Column('ScanMed', db.String(50))
    ScanMVR = db.Column('ScanMVR', db.String(50))
    ScanTwic = db.Column('ScanTwic', db.String(50))
    JobStart = db.Column('JobStart',db.DateTime)
    JobEnd = db.Column('JobEnd', db.DateTime)
    Tagid = db.Column('Tagid', db.String(25))
    Pin = db.Column('Pin', db.String(45))
    CDLnum = db.Column('CDLnum', db.String(45))
    CDLstate = db.Column('CDLstate', db.String(20))
    CDLissue = db.Column('CDLissue', db.DateTime)
    CDLexpire = db.Column('CDLexpire', db.DateTime)
    DOB = db.Column('DOB', db.DateTime)
    MedExpire = db.Column('MedExpire', db.DateTime)
    TwicExpire = db.Column('TwicExpire', db.DateTime)
    TwicNum = db.Column('TwicNum', db.String(45))
    PreScreen = db.Column('PreScreen', db.DateTime)
    LastTested = db.Column('LastTested', db.DateTime)
    Active = db.Column('Active', db.Integer)


    def __init__(self, Name, Addr1, Addr2, Phone, Email, Truck, Tag, ScanCDL, ScanMed, ScanMVR, ScanTwic, JobStart,
                 JobEnd, Tagid, Pin, CDLnum, CDLstate, CDLissue, CDLexpire, DOB, MedExpire, TwicExpire, TwicNum,
                 PreScreen, LastTested, Active):
        self.Name = Name
        self.Addr1 = Addr1
        self.Addr2 = Addr2
        self.Phone = Phone
        self.Email = Email
        self.Truck = Truck
        self.Tag = Tag
        self.ScanCDL = ScanCDL
        self.ScanMed = ScanMed
        self.ScanMVR = ScanMVR
        self.ScanTwic = ScanTwic
        self.JobStart = JobStart
        self.JobEnd = JobEnd
        self.Tagid = Tagid
        self.Pin = Pin
        self.CDLnun = CDLnum
        self.CDLstate = CDLstate
        self.CDLissue = CDLissue
        self.CDLexpire = CDLexpire
        self.DOB = DOB
        self.MedExpire = MedExpire
        self.TwicExpire = TwicExpire
        self.TwicNum = TwicNum
        self.PreScreen = PreScreen
        self.LastTested = LastTested
        self.Active = Active
