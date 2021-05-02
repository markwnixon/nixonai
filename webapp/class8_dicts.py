# These are dictionary setups that control the look, feel, and functionality of the class8 view screens
from webapp.CCC_system_setup import companydata
from flask import request
co = companydata()

genre = 'Trucking'
jobcode = co[10] + genre[0]

Trucking_genre = {'table': 'Orders',
                  'genre_tables': ['Orders', 'Interchange', 'Customers', 'Services', 'Summaries'],
                  'genre_tables_on': ['on', 'off', 'off', 'off'],
                  'quick_buttons': ['New Job', 'Edit Item', 'Edit Invoice',  'Receive Payment'],
                  'table_filters': [{'Date Filter': ['Last 60 Days', 'Last 120 Days', 'Last 180 Days', 'Last Year', 'This Year', 'Show All']},
                                    {'Pay Filter': ['Uninvoiced', 'Unrecorded', 'Unpaid', 'InvoSummaries', 'Show All']},
                                    {'Haul Filter': ['Not Started', 'In-Progress', 'Incomplete', 'Completed',
                                                     'Show All']},
                                    {'Color Filter': ['Haul', 'Invoice', 'Both']}],
                  'task_boxes': [{'Adding': ['New Job', 'New Customer', 'New Interchange', 'New Service', 'New From Copy',
                                             'New Manifest', 'Upload Source', 'Upload Proof']},
                                 {'Editing': ['Edit Item', 'Match', 'Accept', 'Haul+1', 'Haul-1', 'Haul Done', 'Inv+1',
                                                 'Inv-1', 'Inv Emailed', 'Set Col To']},
                                 {'Money Flow': ['Edit Invoice', 'Edit Summary Inv', 'Send Package', 'Receive Payment',
                                                  'Receive by Acct']},
                                 {'View Docs': ['Source', 'Proof', 'Manifest', 'Interchange', 'Invoice',
                                                'Paid Invoice', 'Package']},
                                 {'Undo': ['Delete Item', 'Undo Invoice', 'Undo Payment']},
                                 {'Tasks': ['Street Turn', 'Unpulled Containers', 'Assign Drivers', 'Driver Hours',
                                            'Truck Logs', 'CMA-APL', 'Container Update']}],
                  'container_types': ['40\' GP 9\'6\"', '40\' RS 9\'6\"', '40\' GP 8\'6\"', '40\' RS 8\'6\"', '40\' FR',
                                      '20\' GP 8\'6\"', '20\' VH 8\'6\"', '45\' GP 9\'6\"', '45\' VH 9\'6\"',
                                      '53\' Dry', 'LCL', 'RORO'],
                  'haul_types': ['Dray Import', 'Dray Export', 'Import Extra Stop', 'Export Extra Stop', 'OTR Standard', 'OTR Extra Stop', 'Transload Only', 'Dray-Transload', 'Transload-Deliver', 'Dray-Transload-Deliver'],
                  'load_types': ['Load In', 'Load Out', 'Empty In', 'Empty Out'],
                  'document_profiles'  : {
                                        'Custom' : ['Source', 'Proofs', 'Invoice', 'Gate Tickets'],
                                        'Signed Load Con' : ['Source','0','0','0'],
                                        'Update w/Source'   : ['Source','0','0','0'],
                                        'Update w/Proof'    : ['Proofs','0','0','0'],
                                        'Update w/Invoice'    : ['Invoice','0','0','0'],
                                        'Paid Invoice'    : ['Invoice','0','0','0'],
                                        'Update w/Gate' : ['Gate Tickets','0','0','0'],
                                        'Completed IP' : ['Invoice', 'Proofs','0','0'],
                                        'Completed IPS' : ['Invoice', 'Proofs', 'Source','0'],
                                        'Completed IPSG' : ['Invoice', 'Proofs', 'Source', 'Gate Tickets']
                                      },
                  'image_stamps': {
                      'X': ['x.png', 'stamps', .2],
                      'Check': ['check.png', 'stamps', .5],
                      'Paid': ['paid.png', 'stamps', 1]
                  },
                  'signature_stamps': {
                      'Mark': ['mark.png', 'signatures', .2],
                      'Norma': ['norma.png', 'signatures', .2]
                  },
                  'task_mapping': {'Job':'Orders', 'Customer':'Customers', 'Service':'Services', 'Interchange':'Interchange',
                                   'Source':'CT', 'Proof':'CT', 'View':'CT'},
                  'task_box_map': {
                                    'Quick' :
                                        {
                                            'New Job' : ['Table_Selected', 'New', 'Orders'],
                                            'Edit Item' : ['Single_Item_Selection', 'Edit', 'Form'],
                                            'Edit Invoice' : ['Single_Item_Selection', 'MakeInvoice', 'Invoice'],
                                            'Receive Payment' : ['Single_Item_Selection', 'ReceivePay', 'PayInvoice']
                                        },
                                    'Adding':
                                        {
                                         'New Job': ['Table_Selected', 'New', 'Orders'],
                                         'New Customer' : ['Table_Selected', 'New', 'Customers'],
                                         'New Interchange' : ['Table_Selected', 'New', 'Interchange'],
                                         'New Service' : ['Table_Selected', 'New', 'Services'],
                                         'New From Copy' : ['Single_Item_Selection', 'NewCopy', ''],
                                         'New Manifest' : ['Single_Item_Selection', 'New_Manifest', ''],
                                         'Upload Source' : ['Single_Item_Selection', 'Upload', 'Source'],
                                         'Upload Proof' : ['Single_Item_Selection', 'Upload', 'Proof']
                                         },

                                    'Editing':
                                        {
                                         'Edit Item' : ['Single_Item_Selection', 'Edit', 'Form'],
                                         'Match': ['Two_Item_Selection', 'Match', ''],
                                         'Accept': ['All_Item_Selection', 'Accept', ''],
                                         'Haul+1': ['All_Item_Selection', 'Status', 'Haul+1'],
                                         'Haul-1': ['All_Item_Selection', 'Status', 'Haul-1'],
                                         'Haul Done': ['All_Item_Selection', 'Status', 'Haul Done'],
                                         'Inv+1': ['All_Item_Selection', 'Status', 'Inv+1'],
                                         'Inv-1': ['All_Item_Selection', 'Status', 'Inv-1'],
                                         'Inv Emailed': ['All_Item_Selection', 'Status', 'Inv Emailed'],
                                         'Set Col To': ['All_Item_Selection', 'SetCol', '']
                                        },

                                    'Money Flow':
                                        {
                                         'Edit Invoice' : ['Single_Item_Selection', 'MakeInvoice', 'Invoice'],
                                         'Edit Summary Inv' : ['One_Table_Multi_Item_Selection', 'MakeSummary', 'Invoice'],
                                         'Send Package' : ['Single_Item_Selection', 'MakePackage', 'Package'],
                                         'Receive Payment' : ['Single_Item_Selection', 'ReceivePay', 'PayInvoice'],
                                         'Receive by Acct' : ['No_Selection_Plus_Display_Plus_Left_Panel_Change', 'ReceiveByAccount', '']
                                        },

                                    'View Docs':
                                        {
                                         'Source' : ['Single_Item_Selection', 'View', 'Source'],
                                         'Proof' : ['Single_Item_Selection', 'View', 'Proof'],
                                         'Manifest' : ['Single_Item_Selection', 'View', 'Manifest'],
                                         'Interchange' : ['Single_Item_Selection', 'View', 'Gate'],
                                         'Invoice' : ['Single_Item_Selection', 'View', 'Invoice'],
                                         'Paid Invoice' : ['Single_Item_Selection', 'View', 'PaidInvoice'],
                                         'Package' : ['Single_Item_Selection', 'View', 'Package']
                                         },

                                    'Undo':
                                        {
                                          'Delete Item': ['All_Item_Selection', 'Undo', 'Delete'],
                                          'Undo Invoice': ['All_Item_Selection', 'Undo', 'Invoice'],
                                          'Undo Payment': ['All_Item_Selection', 'Undo', 'Payment']
                                        },
                                    'Tasks':
                                        {
                                          'Street Turn': ['No_Selection_Plus_Display', 'Street_Turn', 'None'],
                                          'Unpulled Containers': ['No_Selection_Plus_Display', 'Unpulled_Containers', 'None'],
                                          'Assign Drivers': ['No_Selection_Plus_Display_Plus_Left_Panel_Change', 'Assign_Drivers', 'None'],
                                          'Driver Hours': ['No_Selection_Plus_Display_Plus_Left_Panel_Change', 'Driver_Hours', 'None'],
                                          'Driver Payroll': ['No_Item_Selection', 'Driver_Payroll', 'None'],
                                          'Truck Logs': ['No_Item_Selection', 'Truck_Logs', 'None'],
                                          'CMA-APL': ['No_Selection_Plus_Display', 'CMA_APL', 'None'],
                                          'Container Update': ['No_Display', 'Container_Update', 'None']
                                        }

                                    }
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
#'haul_types': ['Dray Import', 'Dray Export', 'Import Extra Stop', 'Export Extra Stop', 'OTR Standard', 'OTR Extra Stop', 'Transload Only', 'Dray-Transload', 'Transload-Deliver', 'Dray-Transload-Deliver'],
Orders_setup = {'name' : 'Trucking Job',
                'table': 'Orders',
                'filter': None,
                'filterval': None,
                'checklocation': 9,
                'creators': ['Jo'],
                'ukey': 'Jo',
                'simplify': ['Job','Job Detail','Money','Docs','Dispatch','Hidden'],
                'entry data': [['Jo', 'JO', 'JO', jobcode, 'text', 0, 'ok', 'cc', None, 'Always'],
                               ['Order', 'Order', 'Customer Ref No.', 'text', 'text', 0, 'ok', 'cc', None, 'Job'],
                               ['Shipper', 'Shipper', 'Select Customer', 'select', 'customerdata', 0, 'ok', 'cl', 15, 'Always'],
                               ['HaulType', 'HaulType', 'Select Haul Type', 'select', 'haul_types', 0, 'ok', 'cl', None, 'Job'],
                               ['Booking', 'Release', 'Release', 'text', 'text', 0, 'ok', 'cc', None, 'Job'],
                               ['Container', 'Container', 'Container', 'text', 'concheck', 0, 'ok', 'cc', None, 'Job'],
                               ['Type', 'ConType', 'Select Container Type', 'select', 'container_types', 0, 'ok', 'cc', None, 'Job'],
                               ['Chassis', 'Chassis', '', '', 'text', 0, 'ok', 'cc', None, 'Job'],
                               ['Amount', 'Base$', 'Base Charge', 'text', 'float', 0, 'ok', 'cr', None, 'Money'],
                               ['InvoTotal', 'Invo$', 'Total Charge', 'text', 'float', 0, 'ok', 'cr', None, 'Money'],
                               ['Dropblock1', 'Load At', 'Load At', 'multitext', 'dropblock1', 0, 'Shipper', 'll', None, 'Job Detail'],
                               ['Date', 'Load Date', 'Pick Up Date', 'date', 'date', 0, 'ok', 'cc', None, 'Job'],
                               ['Dropblock2', 'Deliver To', 'Deliver To', 'multitext', 'dropblock2', 0, 'Shipper', 'll', None, 'Job Detail'],
                               ['Date2', 'Del Date', 'Delivery Date', 'date', 'date', 0, 'ok', 'cc', None, 'Job'],
                               ['Dropblock3', 'Third Location', 'Third Location', 'multitext', 'dropblock3', 0, 'Shipper', 'll', None, 'Job Detail'],
                               ['Date3', 'Third Date', 'Third Date', 'date', 'date', 0, 'ok', 'cc', None, 'Job Detail'],
                               ['Driver', 'Driver', 'Select Driver',  'select', 'driverdata', 0, 'ok', 'cc', None, 'Dispatch'],
                               ['Truck', 'Truck', 'Select Truck', 'select', 'truckdata', 0, 'ok', 'cc', None, 'Dispatch'],
                               ['Commodity', 'Commodity', 'Commodity', 'text', 'text', 0, 'ok', 'cc', None, 'Dispatch'],
                               ['Packing', 'Packing', 'Packing', 'text', 'text', 0, 'ok', 'cc', None, 'Dispatch'],
                               ['Seal', 'Seal', 'Seal', 'text', 'text', 0, 'ok', 'cc', None, 'Dispatch'],
                               ['Pickup', 'Pickup', 'Pickup No.', 'text', 'text', 0, 'ok', 'cc', None, 'Dispatch'],
                               ['Description', 'Description', 'Special Instructions', 'multitext', 'text', 0, 'ok', '00', None, 'Dispatch'],
                               ['Label', 'Label', 'InvoSummary', 'text', 'text', 0, 'ok', 'cc', None, 'Hidden']
                               ],
                'hidden data' : [
                                ['Company', 'hidden', 'Dropblock1'],
                                ['Company2','hidden', 'Dropblock2'],
                                ['Location3', 'hidden', 'Dropblock3']
                                ],
                'colorfilter': ['Hstat','Istat'],
                'filteron':  ['Date', 'Invoice', 'Haul'],
                'side data': [{'customerdata': ['People', 'Ptype', 'Trucking', 'Company']},
                              {'driverdata': ['Drivers', 'Active', 1, 'Name']},
                              {'truckdata': ['Vehicles', 'Active', 1, 'Unit']},
                              {'dropblock1': ['Orders', 'Shipper', 'get_Shipper', 'Company']},
                              {'dropblock2': ['Orders', 'Shipper', 'get_Shipper', 'Company2']}],
                'jscript': 'dtTrucking',
                'documents': ['Source', 'Proof', 'Interchange', 'Invoice', 'Paid Invoice'],
                'source': ['vorders', 'Source', 'Jo'],
                'copyswaps' : {},
                'haulmask' : {
                                'release': ['Release: BOL', 'Release: Booking', 'Release: BOL', 'Release: Booking', 'OTR Release BOL', 'OTR Release BOL', 'Transload Release', 'Release: BOL', 'Release: BOL', 'Release: BOL'],
                                'container': ['Container', 'Container', 'Container', 'Container', 'Trailer No.', 'Trailer No.', 'Trailer No.', 'Container', 'Trailer No.', 'Container'],
                                'load1': ['Pick Up and Return', 'Pick Up and Return', 'Pick Up and Return', 'Pick Up and Return', 'Pick Up and Return', 'Pick Up From'],
                                'load1date': ['PickUp/Return Date', 'PickUp/Return Date', 'PickUp/Ret Date', 'Pick Up Empty Date', 'Pick Up Load Date', 'Pick Up Load Date', 'Pick Up Date'],
                                'load2': ['Deliver To', 'Load At', 'Deliver To', 'Load At', 'Deliver To'],
                                'load2date': ['Delivery Date', 'Load Empty Date', 'Delivery Date', 'Load Empty Date', 'Delivery Date', 'Deliver Stop1 Date', 'Pick Up Date', 'Transload Date'],
                                'load3': ['no', 'no', 'Stop2', 'Stop2', 'no'],
                                'load3date': ['no', 'no', 'Stop2 Date', 'Stop2 Date', 'no']
                              },
                'matchfrom':    {
                                 'Orders': ['Shipper', 'Type', 'Company', 'Company2', 'Dropblock1', 'Dropblock2', 'Commodity', 'Packing'],
                                 'Interchange': [['Booking', 'Release'], ['Container', 'Container'], ['Type', 'ConType'], ['Chassis', 'Chassis']],
                                 'Customers': [['Shipper', 'Shipper']],
                                 'Services': []
                                },
                'invoicetypes' : {
                                    'Dray Import' : {
                                                        'Top Blocks' : ['Bill To', 'Pickup and Return for Dray Import', 'Deliver To'],
                                                        'Middle Blocks' : ['Order #', 'BOL #', 'Container #', 'Job Start', 'Job Finished'],
                                                        'Middle Items' : ['Order', 'Booking', 'Container', 'Date', 'Date2'],
                                                        'Lower Blocks' : ['Quantity', 'Item Code', 'Description', 'Price Each', 'Amount']
                                                        } ,

                                    'Dray Export': {
                                        'Top Blocks': ['Bill To', 'Pickup and Return for Dray Export', 'Load At'],
                                        'Middle Blocks': ['Order #', 'Booking #', 'Container #', 'Job Start', 'Job Finished'],
                                        'Middle Items' : ['Order', 'Booking', 'Container', 'Date', 'Date2'],
                                        'Lower Blocks': ['Quantity', 'Item Code', 'Description', 'Price Each', 'Amount']
                                                      },
                                    'Trailer Moves': {
                                        'Top Blocks': ['Bill To', 'Location Start', 'Location Included'],
                                        'Middle Blocks': ['Order #', 'Trailer #', 'Trailer #', 'Job Start', 'Job Finished'],
                                        'Middle Items' : ['Order', 'Container', 'Booking', 'Date', 'Date2'],
                                        'Lower Blocks': ['Quantity', 'Item Code', 'Description', 'Price Each', 'Amount']
                                                     },
                                     'OTR':         {
                                          'Top Blocks': ['Bill To', 'Pickup Location', 'Delivery Location'],
                                          'Middle Blocks': ['Order #', 'Unit #', 'Trailer #', 'Job Start',
                                                            'Job Finished'],
                                          'Middle Items' : ['Order', 'Truck', 'Container', 'Date', 'Date2'],
                                          'Lower Blocks': ['Quantity', 'Item Code', 'Description', 'Price Each',
                                                           'Amount']
                                                    }

                                },
                'summarytypes': {
                                    'Invoice': {
                                            'Top Blocks': ['Bill To', 'Pickup and Return for Dray Import', 'Deliver To'],
                                            'Middle Blocks': ['Order #', 'BOL #', 'Container #', 'Job Start', 'Job Finished'],
                                            'Middle Items': ['Order', 'Booking', 'Container', 'Date', 'Date2'],
                                            'Lower Blocks': ['JO', 'Gate Out-In', 'Booking', 'Container', 'Description/Notes', 'Amt']
                                        }

                                    }
                }

Interchange_setup = {'name' : 'Interchange Ticket',
                     'table': 'Interchange',
                     'filter': None,
                     'filterval': None,
                     'checklocation': 1,
                     'creators': [],
                     'ukey': 'Release',
                     'simplify': ['Ticket', 'Extras'],
                     'entry data': [['Jo', 'JO', '', '', 'text', 0, 'ok', 'cc', None, 'Always'],
                                    ['Company', 'Company', '', '', 'text', 0, 'ok', 'cl', 15, 'Always'],
                                    ['Release', 'Release', 'Release', 'text', 'text', 0, 'ok', 'cc', None, 'Ticket'],
                                    ['Container', 'Container', 'Container', 'text', 'concheck', 0, 'ok', 'cc', None, 'Ticket'],
                                    ['ConType', 'Equip Type', 'Equip Type', 'select', 'container_types', 0, 'ok', 'cc', None, 'Ticket'],
                                    ['Type', 'Load Type', 'Load Type', 'select', 'load_types', 0, 'ok', 'cc', None, 'Ticket'],
                                    ['Chassis', 'Chassis', '', '', 'text', 0, 'ok', 'cc', None, 'Ticket'],
                                    ['Date', 'Load Date', 'Load Date', 'date', 'date', 0, 'ok', 'cc', None, 'Ticket'],
                                    ['Time', 'Gate Time', 'Gate Time', 'time', 'time', 0, 'ok', 'cc', None, 'Ticket'],
                                    ['GrossWt', 'Gross Weight', 'Gross Weight', 'text', 'text', 0, 'ok', 'cc', None, 'Ticket'],
                                    ['TruckNumber', 'Truck Number', 'Truck Number', 'text', 'text', 0, 'ok', 'cc', None, 'Ticket'],
                                    ['Driver', 'Driver', 'Driver', 'text', 'text', 0, 'ok', 'cc', None, 'Extras'],
                                    ['Status', 'Status', 'Status', 'text', 'text', 0, 'ok', 'cc', None, 'Extras']
                                    ],
                     'hidden data' : [],
                     'haulmask' : [],
                     'colorfilter': ['Status'],
                      'filteron':  ['Date'],
                     'side data': [{'customerdata': ['People', 'Ptype', 'Trucking', 'Company']},
                                   {'dropblock1': ['Orders', 'Shipper', 'get_Shipper', 'Company']},
                                   {'dropblock2': ['Orders', 'Shipper', 'get_Shipper', 'Company2']}],
                     'jscript': 'dtHorizontalVerticalExample2',
                     'documents': ['Source'],
                     'source': ['vinterchange', '', 'Container', 'Type'],
                     'copyswaps' : {
                                    'Load In' : 'Empty Out',
                                    'Empty Out' : 'Load In',
                                    'Load Out' : 'Empty In',
                                    'Empty In' : 'Load Out'
                                    },
                     'matchfrom': {
                         'Orders': [['Jo', 'Jo'], ['Company', 'Shipper'] ],
                         'Interchange': [],
                         'Customers': [],
                         'Services': [],
                                    }
                     }

Customers_setup = {'name' : 'Customer',
                   'table': 'People',
                   'filter': 'Ptype',
                   'filterval': 'Trucking',
                   'filter logic': '==',
                   'button flip': None,
                   'checklocation': 1,
                   'creators': [],
                   'ukey' : 'Company',
                   'simplify': [],
                   'entry data': [['Company', 'Company/Name', 'Company/Name', 'text', 'text', 0, 'ok', 'cl', None, 'Always'],
                                  ['Addr1', 'Addr1', 'Address Line 1', 'text', 'text', 0, 'ok', 'cl', None, 'Always'],
                                  ['Addr2', 'Addr2', 'Address Line 2', 'text', 'text', 0, 'ok', 'cl', None, 'Always'],
                                  ['Telephone', 'Telephone', 'Telephone', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                  ['Email', 'Email Status', 'Email Status', 'text', 'text', 0, 'ok', 'cl', None, 'Always'],
                                  ['Associate1', 'Email POD', 'Email POD', 'text', 'text', 0, 'ok', 'cl', None, 'Always'],
                                  ['Associate2', 'Email AP', 'Email AP', 'text', 'text', 0, 'ok', 'cl', None, 'Always'],
                                  ['Date1', 'Added Date', 'Added Date', 'date', 'date', 0, 'ok', 'cc', None, 'Always']],
                   'hidden data' : [],
                   'haulmask': [],
                   'colorfilter': None,
                    'filteron':  [],
                   'side data': [{'customerdata': ['People', 'Ptype', 'Trucking', 'Company']},
                                 {'dropblock1': ['Orders', 'Shipper', 'get_Shipper', 'Company']},
                                 {'dropblock2': ['Orders', 'Shipper', 'get_Shipper', 'Company2']}],
                   'jscript': 'dtHorizontalVerticalExample3',
                   'documents': ['Source'],
                   'source': ['vpersons','', 'Company'],
                   'copyswaps' : {}
                   }

Services_setup = {'name' : 'Service',
                  'table': 'Services',
                  'filter': None,
                  'filterval': None,
                  'checklocation': 1,
                  'creators': [],
                  'ukey': 'Service',
                  'simplify': [],
                  'entry data': [['Service', 'Service', 'Service', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                 ['Price', 'Price', 'Price', 'text', 'dollar', 0, 'ok', 'cc', None, 'Always']],
                  'hidden data' : [],
                  'haulmask': [],
                  'colorfilter': None,
                   'filteron':  [],
                  'side data': [{'customerdata': ['People', 'Ptype', 'Trucking', 'Company']},
                                {'dropblock1': ['Orders', 'Shipper', 'get_Shipper', 'Company']},
                                {'dropblock2': ['Orders', 'Shipper', 'get_Shipper', 'Company2']}],
                  'jscript': 'dtHorizontalVerticalExample4',
                  'documents': ['Source'],
                  'source': ['vservices', ''],
                  'copyswaps' : {}
                  }

Summaries_setup = {'name' : 'Summaries',
                  'table': 'SumInv',
                  'filter': 'Status',
                  'filterval': 0,
                  'filter logic': '>=',
                  'checklocation': 1,
                  'button flip': [['Collapse', 1], ['Expand', 0]],
                  'creators': [],
                  'ukey': 'Si',
                  'simplify': [],
                  'entry data':[['Si', 'SI', 'SI', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                               ['Jo', 'Jo', 'Jo', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                               ['Billto', 'Bill To', 'Bill To',  'text', 'text', 0, 'ok', 'cl', 20, 'Always'],
                               ['InvoDate', 'InvoDate', 'InvoDate',  'date', 'date', 0, 'ok', 'cc', None, 'Always'],
                               ['Begin', 'Gate Out', 'Gate Out', 'date', 'date', 0, 'ok', 'cc', None, 'Always'],
                               ['End', 'Gate In', 'Gate In', 'date', 'date', 0, 'ok', 'cc', None, 'Always'],
                               ['Release', 'Release', 'Release', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                               ['Container', 'Container', 'Container', 'text', 'concheck', 0, 'ok', 'cc', None, 'Always'],
                               ['Type', 'ConType', 'Select Container Type', 'select', 'container_types', 0, 'ok', 'cc', None, 'Always'],
                               ['Amount', 'Amount', 'Amount', 'text', 'float', 0, 'ok', 'cr', None, 'Always'],
                               ['Total', 'Total', 'Total', 'text', 'float', 0, 'ok', 'cr', None, 'Always'],
                               ['Description', 'Description', 'Description', 'multitext', 'text', 0, 'ok', 'cl', None, 'Always'],
                               ['Status', 'Status', 'Status', 'text', 'integer', 0, 'ok', 'cc', None, 'Always'],
                               ['Cache', 'Cache', 'Cache', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                               ],
                  'hidden data' : [],
                  'haulmask': [],
                  'colorfilter': ['Status'],
                   'filteron':  [],
                  'side data': [{'customerdata': ['People', 'Ptype', 'Trucking', 'Company']},
                                {'dropblock1': ['Orders', 'Shipper', 'get_Shipper', 'Company']},
                                {'dropblock2': ['Orders', 'Shipper', 'get_Shipper', 'Company2']}],
                  'jscript': 'dtSummaries',
                  'documents': ['Source'],
                  'source': ['vservices', ''],
                  'copyswaps' : {},
                   'summarytypes': {
                       'Invoice': {
                           'Top Blocks': ['Bill To', 'Pickup and Return for Dray Import', 'Deliver To'],
                           'Middle Blocks': ['Order #', 'BOL #', 'Container #', 'Job Start', 'Job Finished'],
                           'Middle Items': ['Order', 'Booking', 'Container', 'Date', 'Date2'],
                           'Lower Blocks': ['JO', 'Gate Out-In', 'Booking', 'Container', 'Description/Notes', 'Amt']
                       }}
                  }

Invoices_setup = {'name' : 'Invoice',
                  'table': 'Invoices',
                  'filter': None,
                  'filterval': None,
                  'creators': [],
                  'ukey': 'Jo',
                  'simplify': [],
                  'entry data': [['Service', 'Service', 'Service', 'text', 'text', 0, 'ok'],
                                 ['Price', 'Price', 'Price', 'text', 'dollar', 0, 'ok']],
                  'hidden data' : [],
                  'haulmask': [],
                  'colorfilter': None,
                  'side data': [{'customerdata': ['People', 'Ptype', 'Trucking', 'Company']},
                                {'dropblock1': ['Orders', 'Shipper', 'get_Shipper', 'Company']},
                                {'dropblock2': ['Orders', 'Shipper', 'get_Shipper', 'Company2']}],
                  'jscript': 'dtHorizontalVerticalExample4',
                  'documents': ['None'],
                  'source': ['None'],
                  'copyswaps' : {}
                  }

CT_setup = {'table': '0'}

Auto_genre =   {'table': 'Autos',
                  'genre_tables': ['Autos', 'Orders', 'Interchange', 'Customers', 'Services', 'Summaries'],
                  'genre_tables_on': ['on', 'off', 'off', 'off', 'off','off'],
                  'quick_buttons': ['New Job', 'Edit Item', 'Edit Invoice',  'Receive Payment'],
                  'table_filters': [{'Date Filter': ['Last 60 Days', 'Last 120 Days', 'Last 180 Days', 'Last Year', 'This Year', 'Show All']},
                                    {'Pay Filter': ['Uninvoiced', 'Unrecorded', 'Unpaid', 'InvoSummaries', 'Show All']},
                                    {'Haul Filter': ['Not Started', 'In-Progress', 'Incomplete', 'Completed',
                                                     'Show All']},
                                    {'Color Filter': ['Haul', 'Invoice', 'Both']}],
                  'task_boxes': [{'Adding': ['New Job', 'New Customer', 'New Interchange', 'New Service', 'New From Copy',
                                             'New Manifest', 'Upload Purchase', 'Upload Tow BOL', 'Upload Title']},
                                 {'Editing': ['Edit Item', 'Match', 'Accept', 'Haul+1', 'Haul-1', 'Haul Done', 'Inv+1',
                                                 'Inv-1', 'Inv Emailed', 'Set Col To']},
                                 {'Money Flow': ['Edit Invoice', 'Edit Summary Inv', 'Send Package', 'Receive Payment',
                                                  'Receive by Acct']},
                                 {'View Docs': ['Purchase Receipt', 'Tow BOL', 'Title', 'Invoice',
                                                'Paid Invoice', 'Package']},
                                 {'Undo': ['Delete Item', 'Undo Invoice', 'Undo Payment']},
                                 {'Tasks': ['Street Turn', 'Unpulled Containers', 'Assign Drivers', 'Driver Hours',
                                            'Truck Logs', 'CMA-APL', 'Container Update']}],
                  'container_types': ['40\' GP 9\'6\"', '40\' RS 9\'6\"', '40\' GP 8\'6\"', '40\' RS 8\'6\"', '40\' FR',
                                      '20\' GP 8\'6\"', '20\' VH 8\'6\"', '45\' GP 9\'6\"', '45\' VH 9\'6\"',
                                      '53\' Dry', 'LCL', 'RORO'],
                  'haul_types': ['Dray Import', 'Dray Export', 'Import Extra Stop', 'Export Extra Stop', 'OTR Standard', 'OTR Extra Stop', 'Transload Only', 'Dray-Transload', 'Transload-Deliver', 'Dray-Transload-Deliver'],
                  'load_types': ['Load In', 'Load Out', 'Empty In', 'Empty Out'],
                  'document_profiles'  : {
                                        'Custom' : ['Source', 'Proofs', 'Invoice', 'Gate Tickets'],
                                        'Signed Load Con' : ['Source','0','0','0'],
                                        'Update w/Source'   : ['Source','0','0','0'],
                                        'Update w/Proof'    : ['Proofs','0','0','0'],
                                        'Update w/Invoice'    : ['Invoice','0','0','0'],
                                        'Paid Invoice'    : ['Invoice','0','0','0'],
                                        'Update w/Gate' : ['Gate Tickets','0','0','0'],
                                        'Completed IP' : ['Invoice', 'Proofs','0','0'],
                                        'Completed IPS' : ['Invoice', 'Proofs', 'Source','0'],
                                        'Completed IPSG' : ['Invoice', 'Proofs', 'Source', 'Gate Tickets']
                                      },
                  'image_stamps': {
                      'X': ['x.png', 'stamps', .2],
                      'Check': ['check.png', 'stamps', .5],
                      'Paid': ['paid.png', 'stamps', 1]
                  },
                  'signature_stamps': {
                      'Mark': ['mark.png', 'signatures', .2],
                      'Norma': ['norma.png', 'signatures', .2]
                  },
                  'task_mapping': {'Job':'Orders', 'Customer':'Customers', 'Service':'Services', 'Interchange':'Interchange',
                                   'Source':'CT', 'Proof':'CT', 'View':'CT'},
                  'task_box_map': {
                                    'Quick' :
                                        {
                                            'New Job' : ['Table_Selected', 'New', 'Orders'],
                                            'Edit Item' : ['Single_Item_Selection', 'Edit', 'Form'],
                                            'Edit Invoice' : ['Single_Item_Selection', 'MakeInvoice', 'Invoice'],
                                            'Receive Payment' : ['Single_Item_Selection', 'ReceivePay', 'PayInvoice']
                                        },
                                    'Adding':
                                        {
                                         'New Job': ['Table_Selected', 'New', 'Orders'],
                                         'New Customer' : ['Table_Selected', 'New', 'Customers'],
                                         'New Interchange' : ['Table_Selected', 'New', 'Interchange'],
                                         'New Service' : ['Table_Selected', 'New', 'Services'],
                                         'New From Copy' : ['Single_Item_Selection', 'NewCopy', ''],
                                         'New Manifest' : ['Single_Item_Selection', 'New_Manifest', ''],
                                         'Upload Purchase' : ['Single_Item_Selection', 'Upload', 'Source'],
                                         'Upload Tow BOL' : ['Single_Item_Selection', 'Upload', 'Proof'],
                                         'Upload Title' : ['Single_Item_Selection', 'Upload', 'TitleDoc']
                                         },

                                    'Editing':
                                        {
                                         'Edit Item' : ['Single_Item_Selection', 'Edit', 'Form'],
                                         'Match': ['Two_Item_Selection', 'Match', ''],
                                         'Accept': ['All_Item_Selection', 'Accept', ''],
                                         'Haul+1': ['All_Item_Selection', 'Status', 'Haul+1'],
                                         'Haul-1': ['All_Item_Selection', 'Status', 'Haul-1'],
                                         'Haul Done': ['All_Item_Selection', 'Status', 'Haul Done'],
                                         'Inv+1': ['All_Item_Selection', 'Status', 'Inv+1'],
                                         'Inv-1': ['All_Item_Selection', 'Status', 'Inv-1'],
                                         'Inv Emailed': ['All_Item_Selection', 'Status', 'Inv Emailed'],
                                         'Set Col To': ['All_Item_Selection', 'SetCol', '']
                                        },

                                    'Money Flow':
                                        {
                                         'Edit Invoice' : ['Single_Item_Selection', 'MakeInvoice', 'Invoice'],
                                         'Edit Summary Inv' : ['One_Table_Multi_Item_Selection', 'MakeSummary', 'Invoice'],
                                         'Send Package' : ['Single_Item_Selection', 'MakePackage', 'Package'],
                                         'Receive Payment' : ['Single_Item_Selection', 'ReceivePay', 'PayInvoice'],
                                         'Receive by Acct' : ['No_Selection_Plus_Display_Plus_Left_Panel_Change', 'ReceiveByAccount', '']
                                        },

                                    'View Docs':
                                        {
                                         'Purchase Receipt' : ['Single_Item_Selection', 'View', 'Source'],
                                         'Tow BOL' : ['Single_Item_Selection', 'View', 'Proof'],
                                         'Title' : ['Single_Item_Selection', 'View', 'TitleDoc'],
                                         'Invoice' : ['Single_Item_Selection', 'View', 'Invoice'],
                                         'Paid Invoice' : ['Single_Item_Selection', 'View', 'PaidInvoice'],
                                         'Package' : ['Single_Item_Selection', 'View', 'Package']
                                         },

                                    'Undo':
                                        {
                                          'Delete Item': ['All_Item_Selection', 'Undo', 'Delete'],
                                          'Undo Invoice': ['All_Item_Selection', 'Undo', 'Invoice'],
                                          'Undo Payment': ['All_Item_Selection', 'Undo', 'Payment']
                                        },
                                    'Tasks':
                                        {
                                          'Street Turn': ['No_Selection_Plus_Display', 'Street_Turn', 'None'],
                                          'Unpulled Containers': ['No_Selection_Plus_Display', 'Unpulled_Containers', 'None'],
                                          'Assign Drivers': ['No_Selection_Plus_Display_Plus_Left_Panel_Change', 'Assign_Drivers', 'None'],
                                          'Driver Hours': ['No_Selection_Plus_Display_Plus_Left_Panel_Change', 'Driver_Hours', 'None'],
                                          'Driver Payroll': ['No_Item_Selection', 'Driver_Payroll', 'None'],
                                          'Truck Logs': ['No_Item_Selection', 'Truck_Logs', 'None'],
                                          'CMA-APL': ['No_Selection_Plus_Display', 'CMA_APL', 'None'],
                                          'Container Update': ['No_Display', 'Container_Update', 'None']
                                        }

                                    }
                    }

Autos_setup = {'name' : 'Auto Job',
                'table': 'Autos',
                'filter': None,
                'filterval': None,
                'checklocation': 1,
                'creators': ['Jo'],
                'ukey': 'Jo',
                'simplify': ['Job','Tow','Money','Docs'],
                'entry data': [['Jo', 'JO', 'JO', jobcode, 'text', 0, 'ok', 'cc', None, 'Always'],
                               ['Customer', 'Customer', 'Select Customer', 'select', 'customerdata', 0, 'ok', 'cl', 15, 'Always'],
                               ['Source', 'PR', 'Source', 'text', 'text', 0, 'ok', 'cL', None, 'Docs'],
                               ['Year', 'Year', 'Year', 'text', 'text', 0, 'ok', 'cc', None, 'Job'],
                               ['Make', 'Make', 'Make', 'text', 'text', 0, 'ok', 'cl', None, 'Job'],
                               ['Model', 'Model', 'Model', 'text', 'text', 0, 'ok', 'cl', None, 'Job'],
                               ['Color', 'Color', 'Color', 'text', 'text', 0, 'ok', 'cc', None, 'Job'],
                               ['VIN', 'VIN', 'VIN', 'text', 'text', 0, 'ok', 'cc', None, 'Job'],
                               ['TitleDoc', 'TD', 'TitleDoc', 'text', 'text', 0, 'ok', 'cL', None, 'Docs'],
                               ['Title', 'Title', 'Title', 'text', 'text', 0, 'ok', 'cc', None, 'Job'],
                               ['State', 'State', 'State', 'text', 'text', 0, 'ok', 'cc', None, 'Job'],
                               ['EmpWeight', 'Wt', 'EmpWeight', 'text', 'text', 0, 'ok', 'cr', None, 'Job'],
                               ['Value', 'Value', 'Value', 'text', 'text', 0, 'ok', 'll', None, 'Job'],
                               ['Proof', 'TB', 'Proof', 'text', 'text', 0, 'ok', 'cL', None, 'Docs'],
                               ['TowCompany', 'TowCompany', 'TowCompany', 'text', 'dropblock2', 0, 'Shipper', 'll', None, 'Tow'],
                               ['TowCost', 'TowCost', 'TowCost', 'text', 'text', 0, 'ok', '00', None, 'Tow'],
                               ['TowCostEa', 'TowCost', 'towCostEa', 'text', 'text', 0, 'Shipper', 'll', None, 'Tow'],
                               ['Date', 'Date', 'Date',  'date', 'date', 0, 'ok', 'cc', None, 'Work'],
                               ['Date2', 'Date2', 'Date2', 'date', 'date', 0, 'ok', 'cc', None, 'Tow'],
                               ['Pufrom', 'PuFrom', 'PuFrom', 'multitext', 'dropblock1', 0, 'TowCo', 'll', None, 'Work'],
                               ['Delto', 'Delto', 'Delto', 'text', 'text', 0, 'ok', 'cc', None, 'Work'],
                               ['Ncars', 'Ncars', 'Ncars', 'text', 'text', 0, 'ok', '00', None, 'NoShow'],
                               ['Orderid', 'Orderid', 'Orderid', 'text', 'text', 0, 'ok', 'cc', None, 'NoShow'],
                               ['Hjo', 'Hjo', 'Hjo', 'text', 'text', 0, 'ok', 'll', None, 'Tow']
                               ],
                'hidden data' : [],
                'colorfilter': ['Status'],
                'filteron':  ['Date', 'Invoice', 'Haul'],
                'side data': [{'customerdata': ['People', 'Ptype', 'Trucking', 'Company']},
                              {'driverdata': ['Drivers', 'Active', 1, 'Name']},
                              {'truckdata': ['Vehicles', 'Active', 1, 'Unit']},
                              {'dropblock1': ['Autos', 'PuFrom', 'get_TowCo', 'Company']},
                              {'dropblock2': ['Orders', 'Shipper', 'get_Shipper', 'Company2']}],
                'jscript': 'dtTrucking',
                'documents': ['Source', 'Proof', 'Interchange', 'Invoice', 'Paid Invoice'],
                'source': ['vorders', 'Source', 'Jo'],
                'copyswaps' : {},
                'haulmask' : {
                                'release': ['Release: BOL', 'Release: Booking', 'Release: BOL', 'Release: Booking', 'OTR Release BOL', 'OTR Release BOL', 'Transload Release', 'Release: BOL', 'Release: BOL', 'Release: BOL'],
                                'container': ['Container', 'Container', 'Container', 'Container', 'Trailer No.', 'Trailer No.', 'Trailer No.', 'Container', 'Trailer No.', 'Container'],
                                'load1': ['Pick Up and Return', 'Pick Up and Return', 'Pick Up and Return', 'Pick Up and Return', 'Pick Up and Return', 'Pick Up From'],
                                'load1date': ['PickUp/Return Date', 'PickUp/Return Date', 'PickUp/Ret Date', 'Pick Up Empty Date', 'Pick Up Load Date', 'Pick Up Load Date', 'Pick Up Date'],
                                'load2': ['Deliver To', 'Load At', 'Deliver To', 'Load At', 'Deliver To'],
                                'load2date': ['Delivery Date', 'Load Empty Date', 'Delivery Date', 'Load Empty Date', 'Delivery Date', 'Deliver Stop1 Date', 'Pick Up Date', 'Transload Date'],
                                'load3': ['no', 'no', 'Stop2', 'Stop2', 'no'],
                                'load3date': ['no', 'no', 'Stop2 Date', 'Stop2 Date', 'no']
                              },
                'matchfrom':    {
                                 'Orders': ['Shipper', 'Type', 'Company', 'Company2', 'Dropblock1', 'Dropblock2', 'Commodity', 'Packing'],
                                 'Interchange': [['Booking', 'Release'], ['Container', 'Container'], ['Type', 'ConType'], ['Chassis', 'Chassis']],
                                 'Customers': [['Shipper', 'Shipper']],
                                 'Services': []
                                },
                'invoicetypes' : {
                                    'Dray Import' : {
                                                        'Top Blocks' : ['Bill To', 'Pickup and Return for Dray Import', 'Deliver To'],
                                                        'Middle Blocks' : ['Order #', 'BOL #', 'Container #', 'Job Start', 'Job Finished'],
                                                        'Middle Items' : ['Order', 'Booking', 'Container', 'Date', 'Date2'],
                                                        'Lower Blocks' : ['Quantity', 'Item Code', 'Description', 'Price Each', 'Amount']
                                                        } ,

                                    'Dray Export': {
                                        'Top Blocks': ['Bill To', 'Pickup and Return for Dray Export', 'Load At'],
                                        'Middle Blocks': ['Order #', 'Booking #', 'Container #', 'Job Start', 'Job Finished'],
                                        'Middle Items' : ['Order', 'Booking', 'Container', 'Date', 'Date2'],
                                        'Lower Blocks': ['Quantity', 'Item Code', 'Description', 'Price Each', 'Amount']
                                                      },
                                    'Trailer Moves': {
                                        'Top Blocks': ['Bill To', 'Location Start', 'Location Included'],
                                        'Middle Blocks': ['Order #', 'Trailer #', 'Trailer #', 'Job Start', 'Job Finished'],
                                        'Middle Items' : ['Order', 'Container', 'Booking', 'Date', 'Date2'],
                                        'Lower Blocks': ['Quantity', 'Item Code', 'Description', 'Price Each', 'Amount']
                                                     },
                                     'OTR':         {
                                          'Top Blocks': ['Bill To', 'Pickup Location', 'Delivery Location'],
                                          'Middle Blocks': ['Order #', 'Unit #', 'Trailer #', 'Job Start',
                                                            'Job Finished'],
                                          'Middle Items' : ['Order', 'Truck', 'Container', 'Date', 'Date2'],
                                          'Lower Blocks': ['Quantity', 'Item Code', 'Description', 'Price Each',
                                                           'Amount']
                                                    }

                                },
                'summarytypes': {
                                    'Invoice': {
                                            'Top Blocks': ['Bill To', 'Pickup and Return for Dray Import', 'Deliver To'],
                                            'Middle Blocks': ['Order #', 'BOL #', 'Container #', 'Job Start', 'Job Finished'],
                                            'Middle Items': ['Order', 'Booking', 'Container', 'Date', 'Date2'],
                                            'Lower Blocks': ['JO', 'Gate Out-In', 'Booking', 'Container', 'Description/Notes', 'Amt']
                                        }

                                    }
                }