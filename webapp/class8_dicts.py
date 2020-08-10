# These are dictionary setups that control the look, feel, and functionality of the class8 view screens
from webapp.CCC_system_setup import companydata
co = companydata()

genre = 'Trucking'
jobcode = co[10] + genre[0]
Trucking_genre = {'table': 'Orders',
                  'genre_tables': ['Orders', 'Interchange', 'Customers', 'Services'],
                  'genre_tables_on': ['on', 'off', 'off', 'off'],
                  'quick_buttons': ['New Job', 'Edit Item', 'Inv Job', 'Rec Pay'],
                  'table_filters': [{'Date Filter': ['Last 60 Days', 'Last 120 Days', 'Last 180 Days', 'Show All']},
                                    {'Pay Filter': ['Uninvoiced', 'Unrecorded', 'Unpaid', 'Show All']},
                                    {'Haul Filter': ['Not Started', 'In-Progress', 'Incomplete', 'Completed',
                                                     'Show All']},
                                    {'Color Filter': ['Haul', 'Invoice', 'Both']}],
                  'task_boxes': [{'Add Items': ['New Job', 'New Customer', 'New Interchange', 'New Service', 'New From Copy',
                                                'Upload Source', 'Upload Proof', 'Make Manifest']},
                                 {'Edit Items': ['Edit Item', 'Match', 'Accept', 'Haul+1', 'Haul-1', 'Haul Done', 'Inv+1',
                                                 'Inv-1', 'Inv Emailed', 'Set Col To']},
                                 {'Money Items': ['Inv Edit', 'Quote Edit', 'Package Send', 'Rec Payment',
                                                  'Rec by Acct']},
                                 {'View Docs': ['Source', 'Proof', 'Manifest', 'Interchange', 'Invoice',
                                                'Paid Invoice']},
                                 {'Undo': ['Delete Item', 'Undo Invoice', 'Undo Payment']},
                                 {'Tasks': ['Street Turn', 'Unpulled Containers', 'Assign Drivers', 'Driver Hours',
                                            'Driver Payroll', 'Truck Logs', 'Text Output']}],
                  'container_types': ['40\' GP 9\'6\"', '40\' RS 9\'6\"', '40\' GP 8\'6\"', '40\' RS 8\'6\"',
                                      '20\' GP 8\'6\"', '20\' VH 8\'6\"', '45\' GP 9\'6\"', '45\' VH 9\'6\"',
                                      '53\' Dry', 'LCL', 'RORO'],
                  'load_types': ['Load In', 'Load Out', 'Empty In', 'Empty Out'],
                  'task_mapping': {'Job':'Orders', 'Customer':'Customers', 'Service':'Services', 'Interchange':'Interchange',
                                   'Source':'CT', 'Proof':'CT', 'View':'CT'},
                  'task_box_map': {'Add Items':
                                        {'New Job': ['New', 'Job', 'Orders'],
                                         'New Customer' : ['New', 'Customer', 'People', 'Ptype', 'Trucking'],
                                         'New Interchange' : ['New', 'Interchange', 'Interchange'],
                                         'New Service' : ['New', 'Service', 'Services'],
                                         'New From Copy' : ['NewCopy', 'Selected'],
                                         'Upload Source' : ['Upload', 'Source', 'Selected'],
                                         'Upload Proof' : ['Upload', 'Proof', 'Selected']},
                                         'Upload Source': ['Upload Proof', 'Make Manifest']}
                                    }

#Dictionary terms:
#table is name of database table
#filter defines what subdata is required for this data.  Indicate None if there is none
#filterval is the filter value to search on
#creator are values that need to be created by the code instead of input at the screen (Jo's for example)
#       values in the creators must align with database entries and the code will call 'get_'creator' for each creator required
#ukey is the key to use as temporary place holder.  It must be able to hold a 14 character text sequence.  The temporary
#       placeholder is only used to create a database row entry and then recapture it for population of the form data
#entry data is the data in the database row we want to populate from a form.  It does NOT need to include all the database row
#       Each column in the row has a 7 part matrix defining:
#           0 - the value of the database column name from the class variable structure
#           1 - the label placed in the column for display in the app
#           2 - the label placed in the form entry field (usually same as above)
#           3 - the type of form field used (text box, date, select, multitext, or '' to no include in new form),
#               if entry is a creator then this is a variable that contains the data used to call the creator function
#                (ex: nextjo = get_Jo(jobcode) where
#               jobcode is a variable container the necessary information to get the next Jo.
#           4 - data pointer to populate the form field selection box if a selection;
#               otherwise indicates type of error checking on conversion of text or date data:
#               (integer, float, money, container, date, email, phone, ....etc)
#               Select boxes do not need error checks since data comes from the box
#           5 - initial value of success for error check.  =0 presumes fail unless suceeds.  Program changes to 1 if successful.
#           6 - error check message to provide if successful, for multiline text involving dropblocks this provides the data for
#               providing a drop history
Orders_setup = {'table': 'Orders',
                'filter': None,
                'filterval': None,
                'creators': ['Jo'],
                'ukey': 'Jo',
                'entry data': [['Jo', 'JO', 'JO', jobcode, 'text', 0, 'ok'],
                               ['Order', 'Order', 'Customer Ref No.', 'text', 'text', 0, 'ok'],
                               ['Shipper', 'Shipper', 'Select Customer', 'select', 'customerdata', 0, 'ok'],
                               ['Booking', 'Release', 'Release', 'text', 'text', 0, 'ok'],
                               ['Container', 'Container', 'Container', 'text', 'concheck', 0, 'ok'],
                               ['Type', 'ConType', 'Container Type', 'select', 'container_types', 0, 'ok'],
                               ['Chassis', 'Chassis', '', '', 'text', 0, 'ok'],
                               ['Amount', 'Amount', 'Base Charge', 'text', 'float', 0, 'ok'],
                               ['Company', 'Load At', 'Load At', 'multitext', 'dropblock1', 0, 'Shipper'],
                               ['Date', 'Load Date', 'Load Date', 'date', 'date', 0, 'ok'],
                               ['Company2', 'Deliver To', 'Deliver To', 'multitext', 'dropblock2', 0, 'Shipper'],
                               ['Date2', 'Del Date', 'Del Date', 'date', 'date', 0, 'ok'],
                               ['Commodity', 'Commodity', 'Commodity', 'text', 'text', 0, 'ok'],
                               ['Packing', 'Packing', 'Packing', 'text', 'text', 0, 'ok'],
                               ['Seal', 'Seal', 'Seal', 'text', 'text', 0, 'ok'],
                               ['Pickup', 'Pickup', 'Pickup No.', 'text', 'text', 0, 'ok'],
                               ['Description', 'Description', 'Special Instructions', 'multitext', 'text', 0, 'ok']],
                'colorfilter': ['Hstat'],
                'side data': [{'customerdata': ['People', 'Ptype', 'Trucking', 'Company']},
                              {'dropblock1': ['Orders', 'Shipper', 'get_Shipper', 'Company']},
                              {'dropblock2': ['Orders', 'Shipper', 'get_Shipper', 'Company2']}],
                'jscript': 'dtTrucking',
                'documents': ['Source', 'Proof', 'Interchange', 'Invoice', 'Paid Invoice'],
                'source': ['Source', 'Jo']
                }

Interchange_setup = {'table': 'Interchange',
                     'filter': None,
                     'filterval': None,
                     'creators': [],
                     'ukey': 'Release',
                     'entry data': [['Jo', 'JO', '', '', 'text', 0, 'ok'],
                                    ['Company', 'Company', '', '', 'text', 0, 'ok'],
                                    ['Release', 'Release', 'Release', 'text', 'text', 0, 'ok'],
                                    ['Container', 'Container', 'Container', 'text', 'concheck', 0, 'ok'],
                                    ['ConType', 'Equip Type', 'Equip Type', 'select', 'container_types', 0, 'ok'],
                                    ['Type', 'Load Type', 'Load Type', 'select', 'load_types', 0, 'ok'],
                                    ['Chassis', 'Chassis', '', '', 'text', 0, 'ok'],
                                    ['Date', 'Load Date', 'Load Date', 'date', 'date', 0, 'ok'],
                                    ['Time', 'Gate Time', 'Gate Time', 'time', 'time', 0, 'ok'],
                                    ['GrossWt', 'Gross Weight', 'Gross Weight', 'text', 'text', 0, 'ok'],
                                    ['TruckNumber', 'Truck Number', 'Truck Number', 'text', 'text', 0, 'ok'],
                                    ['Driver', 'Driver', 'Driver', 'text', 'text', 0, 'ok'],
                                    ['Status', 'Status', 'Status', 'text', 'text', 0, 'ok']
                                    ],
                     'colorfilter': ['Status'],
                     'side data': [{'customerdata': ['People', 'Ptype', 'Trucking', 'Company']},
                                   {'dropblock1': ['Orders', 'Shipper', 'get_Shipper', 'Company']},
                                   {'dropblock2': ['Orders', 'Shipper', 'get_Shipper', 'Company2']}],
                     'jscript': 'dtHorizontalVerticalExample2',
                     'documents': ['Source'],
                     'source': ['None', 'Container', 'Type']
                     }

Customers_setup = {'table': 'People',
                   'filter': 'Ptype',
                   'filterval': 'Trucking',
                   'creators': [],
                   'ukey' : 'Company',
                   'entry data': [['Company', 'Company/Name', 'Company/Name', 'text', 'text', 0, 'ok'],
                                  ['Addr1', 'Addr1', 'Address Line 1', 'text', 'text', 0, 'ok'],
                                  ['Addr2', 'Addr2', 'Address Line 2', 'text', 'text', 0, 'ok'],
                                  ['Telephone', 'Telephone', 'Telephone', 'text', 'text', 0, 'ok'],
                                  ['Email', 'Email Status', 'Email Status', 'text', 'text', 0, 'ok'],
                                  ['Associate1', 'Email POD', 'Email POD', 'text', 'text', 0, 'ok'],
                                  ['Associate2', 'Email AP', 'Email AP', 'text', 'text', 0, 'ok'],
                                  ['Date1', 'Added Date', 'Added Date', 'date', 'date', 0, 'ok']],
                   'colorfilter': None,
                   'side data': [{'customerdata': ['People', 'Ptype', 'Trucking', 'Company']},
                                 {'dropblock1': ['Orders', 'Shipper', 'get_Shipper', 'Company']},
                                 {'dropblock2': ['Orders', 'Shipper', 'get_Shipper', 'Company2']}],
                   'jscript': 'dtHorizontalVerticalExample3',
                   'documents': ['Source'],
                   'source': ['Source', 'Company']
                   }

Services_setup = {'table': 'Services',
                  'filter': None,
                  'filterval': None,
                  'creators': [],
                  'ukey': 'Service',
                  'entry data': [['Service', 'Service', 'Service', 'text', 'text', 0, 'ok'],
                                 ['Price', 'Price', 'Price', 'text', 'dollar', 0, 'ok']],
                  'colorfilter': None,
                  'side data': [{'customerdata': ['People', 'Ptype', 'Trucking', 'Company']},
                                {'dropblock1': ['Orders', 'Shipper', 'get_Shipper', 'Company']},
                                {'dropblock2': ['Orders', 'Shipper', 'get_Shipper', 'Company2']}],
                  'jscript': 'dtHorizontalVerticalExample4',
                  'documents': ['None'],
                  'source': ['None']
                  }

CT_setup = {'table': '0'}
