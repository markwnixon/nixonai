# These are dictionary setups that control the look, feel, and functionality of the class8 view screens
from webapp.CCC_system_setup import companydata
from flask import request
co = companydata()
# hello this is mark at beelink2
#hello this is ubuntu1700
genre = 'Trucking'
jobcode = co[10] + genre[0]

Trucking_genre = {'table': 'Orders',
                  'genre_tables': ['Orders', 'Interchange', 'Customers', 'Services', 'Summaries', 'Drivers', 'Trucks', 'Pins'],
                  'genre_tables_on': ['on', 'off', 'off', 'off', 'off', 'off', 'off'],
                  'quick_buttons': ['New Job', 'Edit Item', 'Edit Invoice',  'Receive Payment'],
                  'table_filters': [{'Shipper Filter': ['get_Shippers', 'Show All']},
                                    {'Date Filter': ['Last 45 Days', 'Last 90 Days', 'Last 180 Days', 'Last 360 Days', 'This Year', 'Last Year', 'Year Before Last', 'Show All']},
                                    {'Pay Filter': ['Uninvoiced', 'Unrecorded', 'Unsent', 'Unpaid', 'InvoSummaries', 'Show All']},
                                    {'Haul Filter': ['Not Started', 'In-Progress', 'Incomplete', 'Completed',
                                                     'Show All']},
                                    {'Color Filter': ['Haul', 'Invoice', 'Both']},
                                    {'Viewer': ['7x5', '8x4', '9x3', '10x2', 'Top-Bot']}
                                    ],
                  'task_boxes': [{'Adding': ['New Job', 'New Customer', 'New Interchange', 'New Service', 'New From Copy',
                                             'New Manifest', 'Upload Source', 'Upload Proof', 'Upload 2nd Proof', 'Upload RateCon', 'Make Blended Gate']},
                                 {'Editing': ['Edit Item', 'Match', 'Accept', 'Haul+1', 'Haul-1', 'Haul Done', 'Inv+1',
                                                 'Inv-1', 'Inv Emailed', 'Inv Paid', 'Set Col To']},
                                 {'Money Flow': ['Edit Invoice', 'Edit Summary Inv', 'Send Package', 'Receive Payment',
                                                  'Receive by Acct']},
                                 {'View Docs': ['Source', 'Proof', 'Manifest', 'Interchange', 'Invoice',
                                                'Paid Invoice', 'Package']},
                                 {'Undo': ['Delete Item', 'Undo Invoice', 'Undo Payment', 'Undo Docs', 'Undo Docs xSource', 'Undo Proof', 'Undo 2nd Proof', 'Undo RateCon']},
                                 {'Tasks': ['Street Turn', 'Unpulled Containers', 'Exports Pulled', 'Exports Returned', 'Exports Bk Diff', 'Imports Out']}],
                  'container_types': ['40\' GP 9\'6\"', '40\' RS 9\'6\"', '40\' GP 8\'6\"', '40\' RS 8\'6\"', '40\' FR',
                                      '20\' GP 8\'6\"', '20\' VH 8\'6\"', '45\' GP 9\'6\"', '45\' VH 9\'6\"', '40\' UT 9\'6\"', '40\' UT 8\'6\"',
                                      '53\' Dry', 'LCL', 'RORO'],
                  'haul_types': ['Dray Import', 'Dray Export', 'Dray Import DP', 'Dray Export DP','Dray Transfer', 'Dray Import 2T', 'Dray Export 2T', 'Import Extra Stop', 'Export Extra Stop', 'OTR', 'Box Truck', 'Transload Only', 'Dray-Transload', 'Transload-Deliver', 'Dray-Transload-Deliver'],
                  'load_types': ['Load In', 'Load Out', 'Empty In', 'Empty Out', 'Dray Out', 'Dray In'],
                  'delivery_types': ['Hard Time', 'Soft Time', 'Day Window', 'Upon Notice'],
                  'document_profiles'  : {
                                        'Custom' : ['Invoice', 'Proofs', 'Gate Tickets', 'Source'],
                                        'Custom-Invoice' : ['Invoice', 'Proofs', 'Gate Tickets', 'Source'],
                                        'Signed Load Con' : ['Source','0','0','0'],
                                        'Update w/Source'   : ['Source','0','0','0'],
                                        'Update w/Proof'    : ['Proofs','0','0','0'],
                                        'Update w/Invoice'    : ['Invoice','0','0','0'],
                                        'Paid Invoice'    : ['Invoice','0','0','0'],
                                        'Update w/Gate' : ['Gate Tickets','0','0','0'],
                                        'Completed IP' : ['Invoice', 'Proofs','0','0'],
                                        'Completed IPG' : ['Invoice', 'Proofs', 'Gate Tickets','0'],
                                        'Completed IPGS' : ['Invoice', 'Proofs', 'Gate Tickets', 'Source']
                                      },
                  'image_stamps': {
                      'X': ['x.png', 'stamps', .2],
                      'Check': ['check.png', 'stamps', .5],
                      'Paid': ['paid.png', 'stamps', 1],
                      'Factor': ['NOA Stamp.png', 'stamps', 1]
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
                                         'Upload Proof' : ['Single_Item_Selection', 'Upload', 'Proof'],
                                         'Upload 2nd Proof' : ['Single_Item_Selection', 'Upload', 'Proof2'],
                                         'Upload RateCon' : ['Single_Item_Selection', 'Upload', 'RateCon'],
                                         'Make Blended Gate' : ['Single_Item_Selection', 'BlendGate', '']
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
                                         'Inv Paid': ['All_Item_Selection', 'Status', 'Inv Paid'],
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
                                          'Undo Payment': ['All_Item_Selection', 'Undo', 'Payment'],
                                          'Undo Docs': ['All_Item_Selection', 'Undo', 'Docs'],
                                          'Undo Docs xSource': ['All_Item_Selection', 'Undo', 'DocsNotSource'],
                                          'Undo Proof': ['All_Item_Selection', 'Undo', 'xProof'],
                                          'Undo 2nd Proof': ['All_Item_Selection', 'Undo', 'yProof'],
                                          'Undo RateCon': ['All_Item_Selection', 'Undo', 'xRateCon']
                                        },
                                    'Tasks':
                                        {
                                          'Street Turn': ['No_Selection_Plus_Display', 'Street_Turn', 'None'],
                                          'Unpulled Containers': ['No_Selection_Plus_Display', 'Unpulled_Containers', 'None'],
                                          'Exports Pulled': ['No_Selection_Plus_Display', 'Exports_Pulled', 'None'],
                                          'Exports Returned': ['No_Selection_Plus_Display', 'Exports_Returned', 'None'],
                                          'Exports Bk Diff': ['No_Selection_Plus_Display', 'Exports_Bk_Diff', 'None'],
                                          'Imports Out': ['No_Selection_Plus_Display', 'Imports_Out', 'None']
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
                'checklocation': 4,
                'creators': ['Jo'],
                'ukey': 'Jo',
                'simplify': ['Min','Docs','Job', 'Gate', 'Money','Job Detail','Dispatch','Hidden'],
                'entry data': [['Jo', 'JO', 'JO', jobcode, 'text', 0, 'ok', 'cc', None, 'Always'],
                               ['Order', 'Order', 'Customer Ref No.', 'text', 'text', 0, 'ok', 'cc', None, 'Job'],
                               ['Shipper', 'Shipper', 'Select Customer', 'select', 'customerdata', 0, 'ok', 'cl', 15, 'Always'],
                               ['Source', 'DO', 'Source', 'text', None, 0, 'ok', 'cL', None, 'Docs'],
                               ['RateCon', 'RC', 'RateCon', 'text', None, 0, 'ok', 'cL', None, 'Docs'],
                               ['Proof', 'P1', 'Proof', 'text', None, 0, 'ok', 'cL', None, 'Docs'],
                                ['Proof2', 'P2', 'Proof', 'text', None, 0, 'ok', 'cL', None, 'Docs'],
                                ['Manifest', 'MF', 'Manifest', 'text', None, 0, 'ok', 'cL', None, 'Docs'],
                               ['Gate', 'GT', 'Gate', 'text', None, 0, 'ok', 'cL', None, 'Docs'],
                               ['Invoice', 'IV', 'Invoice', 'text', None, 0, 'ok', 'cL', None, 'Docs'],
                                ['Package', 'PK', 'Package', 'text', None, 0, 'ok', 'cL', None, 'Docs'],
                                ['PaidInvoice', 'PI', 'PaidInvoice', None, 'text', 0, 'ok', 'cL', None, 'Docs'],
                                ['Date3', 'Delivery', 'Delivery Date', 'date', 'date', 0, 'ok', 'cc', None, 'Job'],
                                ['Delivery', 'Dtype', 'Select Delivery Type', 'select', 'delivery_types', 0, 'ok', 'cc', None, 'Job'],
                               ['Time3', 'DelTime', 'DelTime', 'time', 'time', 0, 'ok', 'cc', None, 'Job'],
                               ['HaulType', 'HaulType', 'Select Haul Type', 'select', 'haul_types', 0, 'ok', 'cl', None, 'Job'],
                                ['Type', 'ConType', 'Select Container Type', 'select', 'container_types', 0, 'ok', 'cc', None, 'Job'],
                                ['Booking', 'Release', 'Release', 'text', 'release', 0, 'ok', 'cc', None, 'Job'],
                                ['SSCO', 'SSCO', 'SSCO', 'text', 'text', 0, 'ok', 'cc', None, 'Job'],
                               ['Container', 'Container', 'Container', 'text', 'concheck', 0, 'ok', 'cc', None, 'Job'],
                                ['BOL', 'In-Book', 'In-Book', 'text', 'inbook', 0, 'ok', 'cc', None, 'Job'],
                               ['Chassis', 'Chassis', 'Chassis', 'text', 'text', 0, 'ok', 'cc', None, 'Job'],
                                ['Ship', 'Ship', 'Ship', 'text', 'text', 0, 'ok', 'cc', None, 'Job'],
                                ['Voyage', 'Voyage', 'Voyage', 'text', 'text', 0, 'ok', 'cc', None, 'Job'],
                                ['Date', 'Gate Out', 'Gate Out', 'date', 'date', 0, 'ok', 'cc', None, 'Gate'],
                                ['Date2', 'Gate In', 'Gate In', 'date', 'date', 0, 'ok', 'cc', None, 'Gate'],
                                ['Date4', 'ERD/AAP', 'ERD/AAP', 'date', 'date', 0, 'ok', 'cc', None, 'Dispatch'],
                                ['Date5', 'Cut/LFD', 'Cut/LFD', 'date', 'date', 0, 'ok', 'cc', None, 'Dispatch'],
                                ['Date6', 'Ship Arrive', 'Ship Arrive', 'date', 'date', 0, 'ok', 'cc', None, 'Dispatch'],
                                ['Date7', 'Due Back', 'Due Back', 'date', 'date', 0, 'ok', 'cc', None, 'Dispatch'],
                                ['Date8', 'Return DP', 'Return DP', 'date', 'date', 0, 'ok', 'cc', None, 'Dispatch'],
                               ['Dropblock2', 'Deliver To', 'Deliver To', 'multitext', 'dropblock2', 0, 'Shipper', 'll',None, 'Job'],
                               ['Dropblock1', 'Terminal', 'Terminal', 'multitext', 'dropblock1', 0, 'Shipper', 'll',None, 'Job Detail'],
                               ['Dropblock3', 'Third Location', 'Third Location', 'appears_if', 'HaulType', 0,'Shipper', 'll', None, 'Job Detail'],
                               ['InvoTotal', 'Invo$', 'Total Charge', 'disabled', 'disabled', 0, 'ok', 'cr', None, 'Money'],
                                ['Payments', 'Paid$', 'Payments', 'disabled', 'disabled', 0, 'ok', 'cr', None, 'Money'],
                                ['BalDue', 'Due$', 'BalDue', 'disabled', 'disabled', 0, 'ok', 'cr', None, 'Money'],
                              # ['Date3', 'Third Date', 'Third Date', 'appears_if', 'HaulType', 0, 'ok', 'cc', None, 'Job Detail'],
                               ['Amount', 'Base$', 'Base Charge', 'text', 'quotehistory', 0, 'ok', 'cr', None, 'Job'],
                               ['Quote', 'Quote', 'Quote', 'text', 'quotehistory', 0, 'ok', 'cl', None, 'Job Detail'],
                               ['Driver', 'Driver', 'Select Driver',  'select', 'driverdata', 0, 'ok', 'cc', None, 'Dispatch'],
                               ['Truck', 'Truck', 'Select Truck', 'select', 'truckdata', 0, 'ok', 'cc', None, 'Dispatch'],
                               ['Commodity', 'Commodity', 'Commodity', 'text', 'text', 0, 'ok', 'cc', None, 'Dispatch'],
                               ['Packing', 'Packing', 'Packing', 'text', 'text', 0, 'ok', 'cc', None, 'Dispatch'],
                               ['Seal', 'Seal', 'Seal', 'text', 'text', 0, 'ok', 'cc', None, 'Dispatch'],
                               ['Pickup', 'Pickup', 'Pickup No.', 'text', 'text', 0, 'ok', 'cc', None, 'Dispatch'],
                               ['Description', 'Description', 'Special Instructions', 'multitext', 'text', 0, 'ok', '00', None, 'Dispatch'],
                               ['Label', 'Label', 'InvoSummary', 'text', 'text', 0, 'ok', 'cc', None, 'Hidden'],
                               ['Emailjp', 'Email Job Provider', 'Job Provider Email', 'choose-select', 'emaildata1', 0, 'Shipper', 'll', None, 'Job Detail'],
                                ['Emailoa', 'Email Opp Assist', 'Email Opp Assist', 'choose-select', 'emaildata2', 0, 'Shipper', 'll', None, 'Job Detail'],
                                ['Emailap', 'Email Acct Payable', 'Email Acct Payable', 'choose-select', 'emaildata3', 0, 'Shipper', 'll', None, 'Job Detail'],
                                ['Saljp', 'Job Provider Name', 'Job Provider Name', 'text', 'text', 0, 'ok', 'cl', None, 'Job Detail'],
                                ['Saloa', 'Ops Assist Name', 'Ops Assist Name', 'text', 'text', 0, 'ok', 'cl', None, 'Job Detail'],
                                ['Salap', 'Acct Payable Name', 'Acct Payable Name', 'text', 'text', 0, 'ok', 'cl', None, 'Job Detail']
                               ],
                'hidden data' : [
                                ['Company', 'hidden', 'Dropblock1'],
                                ['Company2','hidden', 'Dropblock2'],
                                ['Location3', 'hidden', 'Dropblock3'],
                                ['Emailjp', 'hidden', 'Emailjp'],
                                ['Emailoa', 'hidden', 'Emailoa'],
                                ['Emailap', 'hidden', 'Emailap'],
                                ['UserMod', 'hidden', 'UserMod']
                                ],
                'defaults': [
                                ['Hstat', -1],
                                ['Istat', -1],
                                ['Proof', None],
                                ['Proof2', None],
                                ['Chassis', None],
                                ['Invoice', None],
                                ['Gate', None],
                                ['Package', None],
                                ['Manifest', None],
                                ['PaidInvoice', None],
                                ['RateCon', None],
                                ['Container', ''],
                                ['SSCO', ''],
                                ['Voyage', ''],
                                ['Ship', ''],
                                ['BOL', ''],
                                ['Driver', None],
                                ['Truck', None],
                                ['Description', '']
                                 ],
                'colorfilter': ['Hstat','Istat'],
                'filteron':  ['Shipper', 'Date', 'Invoice', 'Haul'],
                'side data': [{'customerdata': ['People', [['Ptype', 'Trucking']], 'Company']},
                              {'driverdata': ['Drivers', [['Active', 1]], 'Name']},
                              {'truckdata': ['Vehicles', [['Active', 1]], 'Unit']},
                              {'emaildata1': ['Orders', [['Shipper', 'get_Shipper']], 'Emailjp']},
                                {'emaildata2': ['Orders', [['Shipper', 'get_Shipper']], 'Emailoa']},
                                {'emaildata3': ['Orders', [['Shipper', 'get_Shipper']], 'Emailap']},
                              {'dropblock1': ['Orders', [['Shipper', 'get_Shipper']], 'Company']},
                              {'dropblock2': ['Orders', [['Shipper', 'get_Shipper']], 'Company2']},
                              {'dropblock3': ['Orders', [['Shipper', 'get_Shipper']], 'Location3']}
                              ],

                'default values': {'get_Shipper': 'Fill This Later'},
                'form show': {
                    'New': ['Job', 'Job Detail'],
                    'Edit': ['Job', 'Job Detail', 'Money', 'Dispatch', 'Gate'],
                    'Manifest': ['Job', 'Job Detail', 'Dispatch']
                },
                'form checks': {
                    'New': ['Shipper', 'Booking', 'Container', 'Type', 'HaulType', 'Date3', 'Emailjp', 'Emailoa', 'Emailap'],
                    'Edit': ['Shipper', 'Booking', 'Container', 'Date', 'Date2', 'Type', 'HaulType','Date3','Dropblock1', 'Dropblock2', 'Dropblock3', 'Emailjp', 'Emailoa', 'Emailap'],
                    'Manifest': ['Driver','Shipper', 'Booking', 'Container', 'Date', 'Date2', 'Type', 'HaulType','Date3', 'Dropblock1', 'Dropblock2', 'Dropblock3']
                },
                'appears_if': {
                    'HaulType': ['Dray Import 2T', 'Dray Export 2T', 'Import Extra Stop', 'Export Extra Stop', 'Dray-Transload-Deliver'],
                    'Dropblock3': ['multitext', 'dropblock3'],
                    'Date3': ['date', 'date']
                },

                'jscript': 'dtTrucking',
                'documents': ['Source', 'Proof', 'Interchange', 'Invoice', 'Paid Invoice'],
                'sourcenaming': ['Source_Jo', 'c0', 'Jo'],
                'copyswaps' : {},
                #'haul_types': ['Dray Import', 'Dray Export', 'Dray Import 2T', 'Dray Export 2T', 'Import Extra Stop', 'Export Extra Stop', 'OTR', 'Box Truck', 'Transload Only', 'Dray-Transload', 'Transload-Deliver', 'Dray-Transload-Deliver'],
                'haulmask' : {
                                'release': ['Release: BOL', 'Release: Booking Out', 'Release: BOL', 'Release: Booking Out',    'Release: BOL', 'Release: Booking Out', 'OTR Release', 'no', 'Trailer-In', 'Release: BOL', 'Trailer-In', 'Release: BOL'],
                                'container': ['Container', 'Container', 'Container', 'Container', 'Container', 'Container',    'Trailer No.', 'no', 'Trailer-Out', 'Container', 'Trailer-Out', 'Container'],
                                'inbook': ['no', 'In-Book', 'no', 'In-Book', 'no', 'In-Book',    'no', 'no', 'no','Trailer-Out', 'Delivery Vehicle', 'Delivery Vehicle'],
                                'load1': ['Pick Up and Return', 'Pick Up and Return', 'Pick Up From', 'Pick Up From', 'Pick Up and Return', 'Pick Up and Return',    'Pick Up From', 'Pick Up From', 'no', 'Dray Terminal', 'Deliver To','Dray Terminal'],
                                'load1date': ['PickUp/Return Date', 'PickUp/Return Date', 'PickUp/Ret Date', 'Pick Up Empty Date', 'Pick Up Load Date', 'Pick Up Load Date', 'Pick Up Date', 'Dray Terminal','Pick Up From','Pick Up From'],
                                'load2': ['Deliver To', 'Load At', 'Deliver To', 'Load At', 'Deliver To', 'Load At',     'Deliver To', 'Deliver To','Transload Location','Transload Location','Transload Location','Transload Location'],
                                'load2date': ['Delivery Date', 'Load Empty Date', 'Delivery Date', 'Load Empty Date', 'Delivery Date', 'Deliver Stop1 Date', 'Pick Up Date', 'Transload Date', 'no', 'no'],
                                'load3': ['no', 'no', 'Return To', 'Return To', 'Extra Stop', 'Extra Stop',     'no', 'no', 'no', 'no', 'no', 'Delivery After Transload'],
                                'load3date': ['no', 'no', 'Stop2 Date', 'Stop2 Date', 'no','Stop2 Date','no', 'Stop2 Date','Stop2 Date','Stop2 Date'],
                                'date4': ['Import Available','Export ERD', 'Import Available', 'Export ERD', 'Import Available','Export ERD',    'no','no', 'no','no', 'no', 'no'],
                                'date5': ['Port LFD', 'Export Cut', 'Port LFD', 'Export Cut', 'Port LFD', 'Export Cut',    'no','no', 'no','no', 'no', 'no'],
                                'date6': ['Empty Return LFD', 'Load Return LFD', 'Empty Return LFD', 'Load Return LFD', 'Empty Return LFD', 'Load Return LFD',    'no', 'no', 'no','no', 'no','no'],
                                'chassis': ['Chassis', 'Chassis', 'Chassis', 'Chassis', 'Chassis', 'Chassis',    'no', 'no', 'no','no', 'no','no']
                              },
                'matchfrom':    {
                                 'Orders': ['Shipper', 'Type', 'Company', 'Company2', 'Dropblock1', 'Dropblock2', 'Commodity', 'Packing'],
                                 'Interchange': [['Booking', 'Release'], ['Container', 'Container'], ['Type', 'ConType'], ['Chassis', 'Chassis']],
                                 'Customers': [['Shipper', 'Shipper']],
                                 'Services': []
                                },
                'invoicetypes' : {
                                    'Dray Import' : {
                                                        'Top Blocks' : ['Bill To', 'Pickup/Return Dray Import', 'Deliver To'],
                                                        'Middle Blocks' : ['Order #', 'Job Type', 'BOL #', 'Container #', 'Chassis', 'Pulled', 'Returned'],
                                                        'Middle Items' : ['Order', 'HaulType', 'Booking', 'Container', 'Chassis', 'Date', 'Date2'],
                                                        'Lower Blocks' : ['Quantity', 'Item Code', 'Description', 'Price Each', 'Amount']
                                                        },
                                    'Dray Import DP': {
                                        'Top Blocks': ['Bill To', 'Pickup/Return Dray Import', 'Deliver To'],
                                        'Middle Blocks': ['Order #', 'Job Type', 'BOL #', 'Container #', 'Chassis', 'Pulled',
                                                          'Returned'],
                                        'Middle Items': ['Order', 'HaulType', 'Booking', 'Container', 'Chassis', 'Date', 'Date2'],
                                        'Lower Blocks': ['Quantity', 'Item Code', 'Description', 'Price Each', 'Amount']
                                    },

                                    'Dray Import 2T': {
                                        'Top Blocks': ['Bill To', 'Pickup From 1st Terminal', 'Deliver To', 'Return To 2nd Terminal'],
                                        'Middle Blocks': ['Order #', 'Job Type', 'BOL #', 'Container #', 'Chassis', 'Pulled',
                                                          'Returned'],
                                        'Middle Items': ['Order', 'HaulType', 'Booking', 'Container', 'Chassis', 'Date', 'Date2'],
                                        'Lower Blocks': ['Quantity', 'Item Code', 'Description', 'Price Each', 'Amount']
                                    },

                                    'Dray Export': {
                                        'Top Blocks': ['Bill To', 'Pickup/Return Dray Export', 'Load At'],
                                        'Middle Blocks': ['Order #', 'Job Type', 'Booking #', 'Container #', 'Chassis', 'Pulled', 'Returned'],
                                        'Middle Items' : ['Order', 'HaulType', 'Booking', 'Container', 'Chassis', 'Date', 'Date2'],
                                        'Lower Blocks': ['Quantity', 'Item Code', 'Description', 'Price Each', 'Amount']
                                     },

                                    'Dray Export DP': {
                                        'Top Blocks': ['Bill To', 'Pickup/Return Dray Export', 'Load At'],
                                        'Middle Blocks': ['Order #', 'Job Type', 'Booking #', 'Container #', 'Chassis', 'Pulled',
                                                          'Returned'],
                                        'Middle Items': ['Order', 'HaulType', 'Booking', 'Container', 'Chassis', 'Date', 'Date2'],
                                        'Lower Blocks': ['Quantity', 'Item Code', 'Description', 'Price Each', 'Amount']
                                    },

                                    'Dray Transfer': {
                                        'Top Blocks': ['Bill To', 'Pickup Location', 'Selever Location'],
                                        'Middle Blocks': ['Order #', 'Job Type', 'Booking #', 'Container #', 'Chassis', 'Pulled',
                                                          'Returned'],
                                        'Middle Items': ['Order', 'HaulType', 'Booking', 'Container', 'Chassis', 'Date', 'Date2'],
                                        'Lower Blocks': ['Quantity', 'Item Code', 'Description', 'Price Each', 'Amount']
                                    },

                                    'Dray Export 2T': {
                                        'Top Blocks': ['Bill To', 'Pickup From 1st Terminal', 'Deliver To', 'Return To 2nd Terminal'],
                                        'Middle Blocks': ['Order #', 'Job Type', 'BOL #', 'Container #', 'Chassis', 'Pulled',
                                                          'Returned'],
                                        'Middle Items': ['Order', 'HaulType', 'Booking', 'Container', 'Chassis', 'Date', 'Date2'],
                                        'Lower Blocks': ['Quantity', 'Item Code', 'Description', 'Price Each', 'Amount']
                                    },

                                    'Import Extra Stop': {
                                        'Top Blocks': ['Bill To', 'Pickup/Return Terminal', 'Deliver To', 'Extra Stop'],
                                        'Middle Blocks': ['Order #', 'Job Type', 'BOL #', 'Container #', 'Chassis', 'Pulled',
                                                          'Returned'],
                                        'Middle Items': ['Order', 'HaulType', 'Booking', 'Container', 'Chassis', 'Date', 'Date2'],
                                        'Lower Blocks': ['Quantity', 'Item Code', 'Description', 'Price Each', 'Amount']
                                    },

                                    'Export Extra Stop': {
                                        'Top Blocks': ['Bill To', 'Pickup/Return Terminal', 'Deliver To', 'Extra Stop'],
                                        'Middle Blocks': ['Order #', 'Job Type', 'BOL #', 'Container #', 'Chassis', 'Pulled',
                                                          'Returned'],
                                        'Middle Items': ['Order', 'HaulType', 'Booking', 'Container', 'Chassis', 'Date', 'Date2'],
                                        'Lower Blocks': ['Quantity', 'Item Code', 'Description', 'Price Each', 'Amount']
                                    },


                                    'Box Truck': {
                                        'Top Blocks': ['Bill To', 'Pickup Location', 'Delivery Location'],
                                        'Middle Blocks': ['Order #', 'Unit #', 'Job Type',  'Job Start',
                                                          'Job Finished'],
                                        'Middle Items': ['Order', 'Truck', 'HaulType', 'Date', 'Date2'],
                                        'Lower Blocks': ['Quantity', 'Item Code', 'Description', 'Price Each',
                                                         'Amount']
                                                     },
                                     'OTR':         {
                                          'Top Blocks': ['Bill To', 'Pickup Location', 'Delivery Location'],
                                          'Middle Blocks': ['Order #', 'Unit #', 'Job Type', 'Trailer #', 'Job Start',
                                                            'Job Finished'],
                                          'Middle Items' : ['Order', 'Truck', 'HaulType', 'Container', 'Date', 'Date2'],
                                          'Lower Blocks': ['Quantity', 'Item Code', 'Description', 'Price Each',
                                                           'Amount']
                                                    },
                                    'Transload Only': {
                                        'Top Blocks': ['Bill To', 'Transload Location'],
                                        'Middle Blocks': ['Order #', 'Job Type', 'Trailer In', 'Trailer Out', 'Job Start',
                                                          'Job Finished'],
                                        'Middle Items': ['Order', 'HaulType', 'Booking', 'Container', 'Date', 'Date2'],
                                        'Lower Blocks': ['Quantity', 'Item Code', 'Description', 'Price Each',
                                                         'Amount']
                                    },

                                    'Dray-Transload': {
                                        'Top Blocks': ['Bill To', 'Pickup/Return Terminal', 'Transload Location'],
                                        'Middle Blocks': ['Order #', 'Job Type', 'BOL #', 'Container #', 'Chassis', 'Pulled', 'Returned'],
                                        'Middle Items': ['Order', 'HaulType', 'Booking', 'Container', 'Chassis', 'Date', 'Date2'],
                                        'Lower Blocks': ['Quantity', 'Item Code', 'Description', 'Price Each', 'Amount']
                                    },

                                    'Transload-Deliver': {
                                        'Top Blocks': ['Bill To', 'Transload Location', 'Delivery Location'],
                                        'Middle Blocks': ['Order #', 'Job Type', 'BOL #', 'Trailer-In', 'Delivery Vehicle', 'Pulled',
                                                          'Returned'],
                                        'Middle Items': ['Order', 'HaulType', 'Booking', 'Container', 'BOL', 'Date', 'Date2'],
                                        'Lower Blocks': ['Quantity', 'Item Code', 'Description', 'Price Each', 'Amount']
                                    },

                                    'Dray-Transload-Deliver': {
                                        'Top Blocks': ['Bill To', 'Pickup/Return Terminal', 'Transload Location', 'Delivery Location'],
                                        'Middle Blocks': ['Order #', 'Job Type', 'BOL #', 'Trailer-In', 'Delivery Vehicle', 'Pulled',
                                                          'Returned'],
                                        'Middle Items': ['Order', 'HaulType', 'Booking', 'Container', 'BOL', 'Date', 'Date2'],
                                        'Lower Blocks': ['Quantity', 'Item Code', 'Description', 'Price Each', 'Amount']
                                    }



                                },
                'summarytypes': {
                                    'Invoice': {
                                            'Top Blocks': ['Bill To', 'Pickup and Return for Dray Import', 'Deliver To'],
                                            'Middle Blocks': ['Order #', 'BOL #', 'Container #', 'Job Start', 'Job Finished'],
                                            'Middle Items': ['Order', 'Booking', 'Container', 'Date', 'Date2'],
                                            'Lower Blocks': ['JO', 'Gate Out-In', 'In-Booking', 'Container', 'Description/Notes', 'Amt']
                                        }

                                    }
                }

Interchange_setup = {'name' : 'Interchange Ticket',
                     'table': 'Interchange',
                     'filter': None,
                     'filterval': None,
                     'checklocation': 1,
                     'creators': [],
                     'ukey': 'Container',
                     'simplify': ['Ticket', 'Extras'],
                     'entry data': [['Jo', 'JO', '', '', None, 0, 'ok', 'cc', None, 'Always'],
                                    ['Company', 'Company', '', '', None, 0, 'ok', 'cl', 15, 'Always'],
                                    ['Source', 'GT', 'Gate', 'text', None, 0, 'ok', 'cL', None, 'Always'],
                                    ['Release', 'Release', 'Release', 'text', 'release', 0, 'ok', 'cc', None, 'Ticket'],
                                    ['Container', 'Container', 'Container', 'text', 'concheck', 0, 'ok', 'cc', None, 'Ticket'],
                                    ['ConType', 'Equip Type', 'Equip Type', 'select', 'container_types', 0, 'ok', 'cc', None, 'Ticket'],
                                    ['Type', 'Load Type', 'Load Type', 'select', 'load_types', 0, 'ok', 'cc', None, 'Ticket'],
                                    ['Chassis', 'Chassis', 'Chassis', 'text', 'text', 0, 'ok', 'cc', None, 'Ticket'],
                                    ['Date', 'Gated Date', 'Gated Date', 'date', 'date', 0, 'ok', 'cc', None, 'Ticket'],
                                    ['Time', 'Gate Time', 'Gate Time', 'time', 'time', 0, 'ok', 'cc', None, 'Ticket'],
                                    ['GrossWt', 'Gross Weight', 'Gross Weight', 'text', 'text', 0, 'ok', 'cc', None, 'Ticket'],
                                    ['TruckNumber', 'Truck Number', 'Truck Number', 'text', 'text', 0, 'ok', 'cc', None, 'Ticket'],
                                    ['Driver', 'Driver', 'Select Driver',  'select', 'driverdata',  0, 'ok', 'cc', None, 'Extras'],
                                    ['Status', 'Status', 'Status', 'text', 'text', 0, 'ok', 'cc', None, 'Extras'],
                                    ['Other', 'Notes', 'Other', 'text', 'text', 0, 'ok', 'cc', None, 'Extras']
                                    ],
                     'hidden data' : [],
                     'haulmask' : [],
                     'colorfilter': ['Status'],
                      'filteron':  ['Date'],
                     'side data': [],
                     'default values': {'get_Shipper': 'Fill This Later'},
                     'form show': {
                         'New': ['Ticket'],
                         'Edit': ['Ticket','Extras']
                     },
                     'form checks': {
                         'New': ['Container', 'Type'],
                         'Edit': ['Container', 'Type']
                     },
                     'jscript': 'dtInterchange',
                     'documents': ['Source'],
                     'sourcenaming': [None, None, 'Container', 'Type'],
                     'copyswaps' : {
                                    'Load In' : 'Empty Out',
                                    'Empty Out' : 'Load In',
                                    'Load Out' : 'Empty In',
                                    'Empty In' : 'Load Out',
                                    'Dray Out' : 'Dray In',
                                    'Dray In' : 'Dray Out'
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
                                ['Saljp', 'Job Prov Name', 'Job Prov Name','text', 'text', 0, 'ok', 'cl', None, 'Always'],
                                ['Saloa', 'Ops Assist Name', 'Ops Assist Name', 'text', 'text', 0, 'ok', 'cl', None, 'Always'],
                                ['Salap', 'Acct Paybl Name', 'Acct Payble Name', 'text', 'text', 0, 'ok', 'cl', None, 'Always'],
                                  ['Date1', 'Added Date', 'Added Date', 'date', 'date', 0, 'ok', 'cc', None, 'Always']],
                   'hidden data' : [],
                   'haulmask': [],
                   'colorfilter': None,
                    'filteron':  [],
                   'side data': [],
                   'default values': {'get_Shipper': 'Fill This Later'},
                   'form show': {
                       'New': [ ],
                       'Edit': [ ]
                   },
                   'form checks': {
                       'New': ['Company'],
                       'Edit': ['Company']
                   },
                   'jscript': 'dtHorizontalVerticalExample3',
                   'documents': ['Source'],
                   'sourcenaming': [None, None,'Company'],
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
                                 ['Code', 'Code', 'Code', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                 ['Price', 'Price', 'Price', 'text', 'dollar', 0, 'ok', 'cc', None, 'Always']],
                  'hidden data' : [],
                  'haulmask': [],
                  'colorfilter': None,
                   'filteron':  [],
                  'side data': [],
                  'default values': {'get_Shipper': 'Fill This Later'},
                  'form show': {
                      'New': [],
                      'Edit': []
                  },
                  'form checks': {
                      'New': ['Company'],
                      'Edit': ['Company']
                  },
                  'jscript': 'dtHorizontalVerticalExample4',
                  'documents': [],
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
                               ['Date', 'Date', 'Date',  'date', 'date', 0, 'ok', 'cc', None, 'Always'],
                               ['Begin', 'Gate Out', 'Gate Out', 'date', 'date', 0, 'ok', 'cc', None, 'Always'],
                               ['End', 'Gate In', 'Gate In', 'date', 'date', 0, 'ok', 'cc', None, 'Always'],
                               ['Release', 'Release', 'Release', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                               ['Container', 'Container', 'Container', 'text', 'concheck', 0, 'ok', 'cc', None, 'Always'],
                               ['Type', 'ConType', 'Select Container Type', 'select', 'container_types', 0, 'ok', 'cc', None, 'Always'],
                               ['Amount', 'Amount', 'Amount', 'text', 'float', 0, 'ok', 'cr', None, 'Always'],
                               ['Total', 'Total', 'Total', 'text', 'float', 0, 'ok', 'cr', None, 'Always'],
                               ['Description', 'Description', 'Description', 'multitext', 'text', 0, 'ok', 'cl', None, 'Always'],
                               ['Status', 'Status', 'Status', 'text', 'integer', 0, 'ok', 'cc', None, 'Always']
                               ],
                  'hidden data' : [],
                  'haulmask': [],
                  'colorfilter': ['Status'],
                   'filteron':  [],
                  'side data': [],
                   'default values': {'get_Shipper': 'Fill This Later'},
                   'form show': {
                       'New': [],
                       'Edit': []
                   },
                   'form checks': {
                       'New': [],
                       'Edit': []
                   },
                  'jscript': 'dtSummaries',
                  'documents': ['Source'],
                  'source': ['vservices', ''],
                  'copyswaps' : {},
                   'summarytypes': {
                       'Invoice': {
                           'Top Blocks': ['Bill To', 'Pickup and Return for Dray Import', 'Deliver To'],
                           'Middle Blocks': ['Order #', 'BOL #', 'Container #', 'Job Start', 'Job Finished'],
                           'Middle Items': ['Order', 'Booking', 'Container', 'Date', 'Date2'],
                           'Lower Blocks': ['JO', 'Gate Out-In', 'In-Booking', 'Container', 'Description/Notes', 'Amt']
                       }}
                  }

Drivers_setup = {'name' : 'Drivers',
                 'table': 'Drivers',
                 'filter': None,
                 'filterval': None,
                  'checklocation': 1,
                  'creators': [],
                  'ukey': 'Name',
                  'simplify': [],
                  'entry data': [['Name', 'Name', 'Name', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                 ['Addr1', 'Addr1', 'Addr1', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                 ['Addr2', 'Addr2', 'Addr2', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Phone', 'Phone', 'Phone', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Email', 'Email', 'Email', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Truck', 'Truck', 'Select Truck', 'select', 'truckdata', 0, 'ok', 'cc', None, 'Always'],
                                ['JobStart', 'JobStart', 'JobStart', 'date', 'date', 0, 'ok', 'cc', None, 'Always'],
                                ['JobEnd', 'JobEnd', 'JobEnd', 'date', 'date', 0, 'ok', 'cc', None, 'Always'],
                                ['Tagid', 'Tagid', 'Tagid', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Pin', 'Pin', 'Pin', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['CDLnum', 'CDLnum', 'CDLnum', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['CDLstate', 'CDLstate', 'CDLstate', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['CDLissue', 'CDLissue', 'CDLissue', 'date', 'date', 0, 'ok', 'cc', None, 'Always'],
                                ['CDLexpire', 'CDLexpire', 'CDLexpire', 'date', 'date', 0, 'ok', 'cc', None, 'Always'],
                                ['DOB', 'DOB', 'DOB', 'date', 'date', 0, 'ok', 'cc', None, 'Always'],
                                ['MedExpire', 'MedExpire', 'MedExpire', 'date', 'date', 0, 'ok', 'cc', None, 'Always'],
                                ['TwicExpire', 'TwicExpire', 'TwicExpire', 'date', 'date', 0, 'ok', 'cc', None, 'Always'],
                                ['TwicNum', 'TwicNum', 'TwicNum', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['PreScreen', 'PreScreen', 'PreScreen', 'date', 'date', 0, 'ok', 'cc', None, 'Always'],
                                ['LastTested', 'LastTested', 'LastTested', 'date', 'date', 0, 'ok', 'cc', None, 'Always'],
                                ['Active', 'Active', 'Active', 'text', 'integer', 0, 'ok', 'cc', None, 'Always'],
                                ['Carrier', 'Carrier', 'Carrier', 'text', 'text', 0, 'ok', 'cc', None, 'Always']
                                 ],
                  'hidden data' : [],
                  'haulmask': [],
                  'colorfilter': None,
                   'filteron':  [],
                  'side data': [
                                {'truckdata': ['Vehicles', [['Active', 1]], 'Unit']}
                  ],
                  'default values': {'get_Shipper': 'Fill This Later'},
                  'form show': {
                      'New': [],
                      'Edit': []
                  },
                  'form checks': {
                      'New': ['Company'],
                      'Edit': ['Company']
                  },
                  'jscript': 'dtHorizontalVerticalExample4',
                  'documents': [],
                  'copyswaps' : {}
                  }

Trucks_setup = {'name' : 'Trucks',
                 'table': 'Vehicles',
                 'filter': None,
                 'filterval': None,
                  'checklocation': 1,
                  'creators': [],
                  'ukey': 'Name',
                  'simplify': [],
                  'entry data': [['Active', 'Active', 'Active', 'text', 'integer', 0, 'ok', 'cc', None, 'Always'],
                                 ['Unit', 'Unit', 'Unit', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                 ['Year', 'Year', 'Year', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                 ['Make', 'Make', 'Make', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Model', 'Model', 'Model', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Color', 'Color', 'Color', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['VIN', 'VIN', 'VIN', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Title', 'Title', 'Title', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Plate', 'Plate', 'Plate', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['EmpWeight', 'EmpWeight', 'EmpWeight', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['GrossWt', 'GrossWt', 'GrossWt', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['DOTNum', 'DOTNum', 'DOTNum', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['ExpDate', 'ExpDate', 'ExpDate', 'date', 'date', 0, 'ok', 'cc', None, 'Always'],
                                ['Odometer', 'Odometer', 'Odometer', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Owner', 'Owner', 'Owner', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Status', 'Status', 'Status', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['ServStr', 'StartedService', 'StartedService', 'date', 'date', 0, 'ok', 'cc', None, 'Always'],
                                ['ServStp', 'StoppedService', 'StoppedService', 'date', 'date', 0, 'ok', 'cc', None, 'Always'],
                                ['Ezpassxponder', 'Ezpassxponder', 'Ezpassxponder', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Portxponder', 'Portxponder', 'Portxponder', 'text', 'text', 0, 'ok', 'cc', None, 'Always']
                                 ],
                  'hidden data' : [],
                  'haulmask': [],
                  'colorfilter': None,
                   'filteron':  [],
                  'side data': [],
                  'default values': {'get_Shipper': 'Fill This Later'},
                  'form show': {
                      'New': [],
                      'Edit': []
                  },
                  'form checks': {
                      'New': ['Company'],
                      'Edit': ['Company']
                  },
                  'jscript': 'dtHorizontalVerticalExample5',
                  'documents': [],
                  'copyswaps' : {}
                  }

Pins_setup = {'name' : 'Trucks',
                 'table': 'Pins',
                 'filter': None,
                 'filterval': None,
                  'checklocation': 1,
                  'creators': [],
                  'ukey': 'Name',
                  'simplify': [],
                  'entry data': [['Date', 'Date', 'Date', 'date', 'date', 0, 'ok', 'cc', None, 'Always'],
                                 ['Driver', 'Driver', 'Driver', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                 ['InBook', 'InBook', 'InBook', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                 ['InCon', 'InCon', 'InCon', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['InChas', 'InChas', 'InChas', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['InPin', 'InPin', 'InPin', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['OutBook', 'OutBook', 'OutBook', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['OutCon', 'OutCon', 'OutCon', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['OutPin', 'OutPin', 'OutPin', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['OutChas', 'OutChas', 'OutChas', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Unit', 'Unit', 'Unit', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Tag', 'Tag', 'Tag', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Phone', 'Phone', 'Phone', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Intext', 'Intext', 'Intext', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Outtext', 'Outtext', 'Outtext', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Timeslot', 'Timeslot', 'Timeslot', 'text', 'integer', 0, 'ok', 'cc', None, 'Always'],
                                ['Notes', 'Notes', 'Notes', 'text', 'text', 0, 'ok', 'cc', None, 'Always']
                                 ],
                  'hidden data' : [],
                  'haulmask': [],
                  'colorfilter': ['Unit'],
                  'filteron':  ['Date'],
                  'side data': [],
                  'default values': {'get_Shipper': 'Fill This Later'},
                  'form show': {
                      'New': [],
                      'Edit': []
                  },
                  'form checks': {
                      'New': ['Company'],
                      'Edit': ['Company']
                  },
                  'jscript': 'dtHorizontalVerticalExample5',
                  'documents': [],
                  'copyswaps' : {}
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
                  'side data': [],
                  'jscript': 'dtHorizontalVerticalExample4',
                  'documents': ['None'],
                  'source': ['None'],
                  'copyswaps' : {}
                  }

Trucklog_setup = {'name' : 'Trucklog',
                  'table': 'Trucklog',
                  'filter': None,
                  'filterval': None,
                  'checklocation': 1,
                  'creators': [],
                  'ukey': 'Service',
                  'simplify': [],
                  'entry data': [['Date', 'Date', 'Date', 'date', 'date', 0, 'ok', 'cc', None, 'Always'],
                                 ['Unit', 'Unit', 'Unit', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Tag', 'Tag', 'Tag', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['DriverStart', 'DriverStart', 'DriverStart', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['DriverEnd', 'DriverEnd', 'DriverEnd', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['GPSin', 'GPSin', 'GPSin', 'datetime', 'datetime', 0, 'ok', 'cc', None, 'Always'],
                                ['GPSout', 'GPSout', 'GPSout', 'datetime', 'datetime', 0, 'ok', 'cc', None, 'Always'],
                                ['Shift', 'Shift', 'Shift', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Gotime', 'Gotime', 'Gotime', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Locationstart', 'Locationstart', 'Locationstart', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Distance', 'Distance', 'Distance', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Rdist', 'Rdist', 'Rdist', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Rloc', 'Rloc', 'Rloc', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Odomstart', 'Odomstart', 'Odomstart', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Odomstop', 'Odomstop', 'Odomstop', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Odverify', 'Odverify', 'Odverify', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],

                                ['Maintrecord', 'Maintrecord', 'Maintrecord', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Maintid', 'Maintid', 'Maintid', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Status', 'Status', 'Status', 'text', 'text', 0, 'ok', 'cc', None, 'Always']
                                 ],
                  'hidden data' : [],
                  'haulmask': [],
                  'colorfilter': None,
                   'filteron':  ['Driver'],
                  'side data': [],
                  'default values': {'get_Shipper': 'Fill This Later'},
                  'form show': {
                      'New': [],
                      'Edit': []
                  },
                  'form checks': {
                      'New': ['Company'],
                      'Edit': ['Company']
                  },
                  'jscript': 'dtHorizontalVerticalExample4',
                  'documents': [],
                  'copyswaps' : {}
                  }

CT_setup = {'table': '0'}

Auto_genre =   {'table': 'Autos',
                  'genre_tables': ['Autos', 'Orders', 'Interchange', 'Customers', 'Services', 'Summaries'],
                  'genre_tables_on': ['on', 'off', 'off', 'off', 'off','off'],
                  'quick_buttons': ['New Job', 'Edit Item', 'Edit Invoice',  'Receive Payment'],
                  'table_filters': [{'Date Filter': ['Last 90 Days', 'Last 180 Days', 'Last 360 Days', 'Last Year', 'This Year', 'Show All']},
                                    {'Pay Filter': ['Uninvoiced', 'Unrecorded', 'Unsent', 'Unpaid', 'InvoSummaries', 'Show All']},
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
                                 {'Tasks': ['Street Turn', 'Unpulled Containers']}],
                  'container_types': ['40\' GP 9\'6\"', '40\' RS 9\'6\"', '40\' GP 8\'6\"', '40\' RS 8\'6\"', '40\' FR',
                                      '20\' GP 8\'6\"', '20\' VH 8\'6\"', '45\' GP 9\'6\"', '45\' VH 9\'6\"',
                                      '53\' Dry', 'LCL', 'RORO'],
                  'haul_types': ['Dray Import', 'Dray Export', 'OTR', 'Box Truck', 'Transload Only', 'Dray-Transload', 'Transload-Deliver', 'Dray-Transload-Deliver'],
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
                                          'Unpulled Containers': ['No_Selection_Plus_Display', 'Unpulled_Containers', 'None']
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
               'side data': [{'customerdata': ['People', [['Ptype', 'Trucking']], 'Company']},
                             {'driverdata': ['Drivers', [['Active', 1]], 'Name']},
                             {'truckdata': ['Vehicles', [['Active', 1]], 'Unit']},
                             {'shipdata': ['Ships', [['Active', 1]], 'Ship']},
                             {'dropblock1': ['Orders', [['Shipper', 'get_Shipper']], 'Company']},
                             {'dropblock2': ['Orders', [['Shipper', 'get_Shipper']], 'Company2']},
                             {'dropblock3': ['Orders', [['Shipper', 'get_Shipper']], 'Location3']}
                             ],
               'default values': {'get_Shipper': 'Fill This Later'},
               'form show': {
                   'New': ['Job', 'Tow', 'Work'],
                   'Edit': ['Job', 'Tow', 'Work']
               },
               'form checks': {
                   'New': ['Customer', 'Date', 'Date2'],
                   'Edit': ['Customer', 'Date', 'Date2']
               },
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
                    'Dray Transfer': {
                        'Top Blocks': ['Bill To', 'Pickup Location', 'Drop Off Location'],
                        'Middle Blocks': ['Order #', 'Booking #', 'Container #', 'Job Start', 'Job Finished'],
                        'Middle Items': ['Order', 'Booking', 'Container', 'Date', 'Date2'],
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
                                            'Lower Blocks': ['JO', 'Gate Out-In', 'In-Booking', 'Container', 'Description/Notes', 'Amt']
                                        }

                                    }
                }


Planning_genre =   {'table': 'Orders',
                  'genre_tables': ['Orders', 'Ships', 'Imports', 'Exports', 'PortClosed'],
                  'genre_tables_on': ['on', 'off', 'off', 'off'],
                  'quick_buttons': ['New Job', 'Edit Item', 'Update Planner', 'Mark Delivered'],
                  'table_filters': [{'Date Filter': ['Week Before Last', 'Last Week', 'This Week', 'Next Week', 'Week After Next']},
                                    {'Delivery Filter': ['Unscheduled', 'Yesterday', 'Today', 'Tomorrow', 'This Week', 'Next Week', 'This Month', 'Show All']},
                                    {'Haul Filter': ['Not Started', 'In-Progress', 'Incomplete', 'Completed',
                                                     'Show All']},
                                    {'Color Filter': ['Haul', 'Status', 'Both']},
                                    {'Viewer': ['7x5', '8x4', '9x3', '10x2', 'Top-Bot']}],
                  'task_boxes': [{'Adding': ['New Job', 'New From Copy', 'New Port Closure']},
                                 {'Editing': ['Edit Item', 'Date+1', 'Date-1', 'Haul+1', 'Haul-1', 'Haul Done', 'Inv+1',
                                                 'Inv-1', 'Inv Emailed', 'Set Col To']},
                                 {'View Docs': ['Purchase Receipt', 'Tow BOL', 'Title', 'Invoice',
                                                'Paid Invoice', 'Package']},
                                 {'Undo': ['Delete Item', 'Undo Invoice', 'Undo Payment']},
                                 {'Tasks': ['Street Turn', 'Unpulled Containers']}],
                  'container_types': ['40\' GP 9\'6\"', '40\' RS 9\'6\"', '40\' GP 8\'6\"', '40\' RS 8\'6\"', '40\' FR',
                                      '20\' GP 8\'6\"', '20\' VH 8\'6\"', '45\' GP 9\'6\"', '45\' VH 9\'6\"', '40\' UT 9\'6\"', '40\' UT 8\'6\"',
                                      '53\' Dry', 'LCL', 'RORO'],
                  'delivery_types': ['Hard Time', 'Soft Time', 'Day Window', 'Upon Notice'],
                  'pickupdata': ['Baltimore Seagirt', 'CSX Rail', 'East Coast CES', 'Belts'],
                  'haul_types': ['Dray Import', 'Dray Export', 'Dray Import DP', 'Dray Export DP', 'Dray Transfer', 'Import Extra Stop', 'Export Extra Stop', 'OTR Standard', 'OTR Extra Stop', 'Transload Only', 'Dray-Transload', 'Transload-Deliver', 'Dray-Transload-Deliver'],
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
                                            'New Job' : ['Table_Selected', 'New', 'Newjobs'],
                                            'Edit Item' : ['Single_Item_Selection', 'Edit', 'Form'],
                                            'Update Planner' : ['Table_Selected', 'UpdatePlanner', 'Newjobs'],
                                            'Mark Delivered' : ['Single_Item_Selection', 'MarkDelivered', 'MarkDelivered']
                                        },
                                    'Adding':
                                        {
                                         'New Job': ['Table_Selected', 'New', 'Newjobs'],
                                         'New Port Closure' : ['Table_Selected', 'New', 'PortClosed'],
                                         'New From Copy' : ['Single_Item_Selection', 'NewCopy', '']
                                         },

                                    'Editing':
                                        {
                                         'Edit Item' : ['Single_Item_Selection', 'Edit', 'Form'],
                                         'Match': ['Two_Item_Selection', 'Match', ''],
                                         'Accept': ['All_Item_Selection', 'Accept', ''],
                                         'Date+1': ['All_Item_Selection', 'Status', 'Date+1'],
                                         'Date-1': ['All_Item_Selection', 'Status', 'Date-1'],
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
                                          'Unpulled Containers': ['No_Selection_Plus_Display', 'Unpulled_Containers', 'None']
                                        }

                                    }
                    }

PortClosed_setup = {'name' : 'PortClosed',
                  'table': 'PortClosed',
                  'filter': None,
                  'filterval': None,
                  'checklocation': 1,
                  'creators': [],
                  'ukey': 'Reason',
                  'simplify': [],
                  'entry data': [['Date', 'Date', 'Date', 'date', 'date', 0, 'ok', 'cc', None, 'Always'],
                                 ['Reason', 'Reason', 'Reason', 'text', 'text', 0, 'ok', 'cc', None, 'Always']],
                    'hidden data' : [],
                  'haulmask': [],
                  'default values': None,
                  'colorfilter': None,
                   'filteron':  [],
                  'side data': [],
                  'form show': {
                      'New': [],
                      'Edit': []
                  },
                  'form checks': {
                      'New': ['Company'],
                      'Edit': ['Company']
                  },
                  'jscript': 'dtHorizontalVerticalExample4',
                  'documents': [],
                  'copyswaps' : {}
                  }

Ships_setup = {'name' : 'Ships',
                'table': 'Ships',
                'filter': None,
                'filterval': None,
                'checklocation': 1,
                'creators': [],
                #'ukey': 'Jo',
                'simplify': ['Job','Docs'],
                'entry data': [
                               ['Vessel', 'Vessel', 'Vessel', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
                                ['Code', 'Code', 'Code', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
['Imports', 'Imports', 'Imports', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
['VoyageIn', 'VoyageIn', 'VoyageIn', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
['VoyageOut', 'VoyageOut', 'VoyageOut', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
['SSCO', 'SSCO', 'SSCO', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
['ActArrival', 'ActArrival', 'ActArrival', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
['GenCutoff', 'GenCutoff', 'GenCutoff', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
['RefCutoff', 'RefCutoff', 'RefCutoff', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
['HazCutoff', 'HazCutoff', 'HazCutoff', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
['EstArrival', 'EstArrival', 'EstArrival', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
['EstDeparture', 'EstDeparture', 'EstDeparture', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
['ActDeparture', 'ActDeparture', 'ActDeparture', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
['Update', 'Update', 'Update', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
                               ],
                'hidden data' : [],
                'colorfilter': None,
                'filteron':  [],
               'side data': [{'customerdata': ['People', [['Ptype', 'Trucking']], 'Company']},
                             {'driverdata': ['Drivers', [['Active', 1]], 'Name']},
                             {'truckdata': ['Vehicles', [['Active', 1]], 'Unit']},
                             {'dropblock1': ['Orders', [['Shipper', 'get_Shipper']], 'Company']},
                             {'dropblock2': ['Orders', [['Shipper', 'get_Shipper']], 'Company2']},
                             {'dropblock3': ['Orders', [['Shipper', 'get_Shipper']], 'Location3']}
                             ],
               'default values': {'get_Shipper': 'Fill This Later'},
               'form show': {
                   'New': ['Job', 'Tow', 'Work'],
                   'Edit': ['Job', 'Tow', 'Work']
               },
               'form checks': {
                   'New': ['Customer', 'Date', 'Date2'],
                   'Edit': ['Customer', 'Date', 'Date2']
               },
                'jscript': 'dtTrucking',
                'documents': ['Source', 'Portbyday'],
                'sourcenaming': ['Source_Jo', 'c0', 'Jo'],
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
                                }

                }

Imports_setup = {'name' : 'Imports',
                'table': 'Imports',
                'filter': None,
                'filterval': None,
                'checklocation': 1,
                'creators': [],
                #'ukey': 'Jo',
                'simplify': ['Job','Docs'],
                'entry data': [
                                ['Jo', 'JO', 'JO', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['BOL', 'BOL', 'BOL', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
                                ['Container', 'Container', 'Container', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
                                ['LineStatus', 'LineStatus', 'LineStatus', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
                                ['CustomsStatus', 'CustomsStatus', 'CustomsStatus', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
                                ['OtherHolds', 'OtherHolds', 'OtherHolds', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
                                ['Location', 'Location', 'Location', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
                                ['Position', 'Position', 'Position', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
                                ['PTD', 'PTD', 'PTD', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
                                ['LFD', 'LFD', 'LFD', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
                                ['TermDem', 'TermDem', 'TermDem', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
                                ['NonDem', 'NonDem', 'NonDem', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
                                ['Size', 'Size', 'Size', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
                                ['Vessel', 'Vessel', 'Vessel', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
                                ['Voyage', 'Voyage', 'Voyage', 'text', 'text', 0, 'ok', 'cl', 15, 'Always']
                               ],
                'hidden data' : [],
                'colorfilter': None,
                'filteron':  [],
                'side data': [],
                'default values': None,
               'form show': {
                   'New': ['Job', 'Tow', 'Work'],
                   'Edit': ['Job', 'Tow', 'Work']
               },
               'form checks': {
                   'New': ['Customer', 'Date', 'Date2'],
                   'Edit': ['Customer', 'Date', 'Date2']
               },
                'jscript': 'dtTrucking',
                'documents': None,
                'sourcenaming': ['Source_Jo', 'c0', 'Jo'],
                'source': ['vorders', 'Source', 'Jo'],
                'copyswaps' : {},
                'haulmask' : None,
                'matchfrom': None
                }

Exports_setup = {'name' : 'Exports',
                'table': 'Exports',
                'filter': None,
                'filterval': None,
                'checklocation': 1,
                'creators': [],
                #'ukey': 'Jo',
                'simplify': ['Job','Docs'],
                'entry data': [
                                ['Jo', 'JO', 'JO', 'text', 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Booking', 'Booking', 'Booking', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
                                ['SSCO', 'SSCO', 'SSCO', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
                                ['Vessel', 'Vessel', 'Vessel', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
                                ['Voyage', 'Voyage', 'Voyage', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
                                ['EmptyStart', 'EmptyStart', 'EmptyStart', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
                                ['GeneralBR', 'GeneralBR', 'GeneralBR', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
                                ['ReeferBR', 'ReeferBR', 'ReeferBR', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
                                ['HazBR', 'HazBR', 'HazBR', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
                                ['GeneralCut', 'GeneralCut', 'GeneralCut', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
                                ['ReeferCut', 'ReeferCut', 'ReeferCut', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
                                ['HazCut', 'HazCut', 'HazCut', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
                                ['LoadingAt', 'LoadingAt', 'LoadingAt', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
                                ['Length', 'Length', 'Length', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
                                ['Type', 'Type', 'Type', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
['Height', 'Height', 'Height', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
['Total', 'Total', 'Total', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
['Received', 'Received', 'Received', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
['Delivered', 'Delivered', 'Delivered', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
['Update', 'Update', 'Update', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
['Active', 'Active', 'Active', 'text', 'text', 0, 'ok', 'cl', 15, 'Always'],
['Screen', 'Screen', 'Screen', 'text', 'text', 0, 'ok', 'cl', 15, 'Always']
                               ],
                'hidden data' : [],
                'colorfilter': None,
                'filteron':  [],
                'side data': [],
                'default values': None,
               'form show': {
                   'New': ['Job', 'Tow', 'Work'],
                   'Edit': ['Job', 'Tow', 'Work']
               },
               'form checks': {
                   'New': ['Customer', 'Date', 'Date2'],
                   'Edit': ['Customer', 'Date', 'Date2']
               },
                'jscript': 'dtTrucking',
                'documents': None,
                'sourcenaming': ['Source_Jo', 'c0', 'Jo'],
                'source': ['vorders', 'Source', 'Jo'],
                'copyswaps' : {},
                'haulmask' : None,
                'matchfrom': None
                }

billcode = co[10] + 'B'
Billing_genre =   {'table': 'Bills',
                  'genre_tables': ['Bills', 'Vendors'],
                  'genre_tables_on': ['on', 'off'],
                  'quick_buttons': ['New Bill', 'Edit Item', 'Pay Bill'],
                  'table_filters': [{'Date Filter': ['Last 90 Days', 'Last 180 Days', 'Last 360 Days', 'Last Year', 'This Year', 'Show All']},
                                    {'Pay Filter': ['Unpaid', 'Show All']},
                                    {'Viewer': ['7x5', '8x4', '9x3', '10x2', 'Top-Bot']}],
                  'task_boxes': [{'Adding': ['New Bill', 'New Vendor', 'Upload Bill', 'Upload Payment']},
                                 {'Editing': ['Edit Item', 'Match']},
                                 {'View Docs': ['Bill Source', 'Receipt', 'Pay Record']},
                                 {'Undo': ['Delete Item', 'Undo Payment']},
                                 {'Tasks': ['Detention Report', 'Chassis Report', 'Bill Calendar']}],
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
                  'paymethods': ['Cash', 'Check', 'Credit Card', 'Epay-App', 'Epay-Web', 'PayCargo', 'Wire'],
                  'image_stamps': {
                      'X': ['x.png', 'stamps', .2],
                      'Check': ['check.png', 'stamps', .5],
                      'Paid': ['paid.png', 'stamps', 1]
                  },
                  'signature_stamps': {
                      'Mark': ['mark.png', 'signatures', .2],
                      'Norma': ['norma.png', 'signatures', .2]
                  },
                  'task_mapping': {'Bill':'Bills', 'Vendor':'Vendors',
                                   'Source':'CT', 'Proof':'CT', 'View':'CT'},
                  'task_box_map': {
                                    'Quick' :
                                        {
                                            'New Bill' : ['Table_Selected', 'New', 'Bills'],
                                            'Edit Item' : ['Single_Item_Selection', 'Edit', 'Form'],
                                            'Pay Bill' : ['One_Table_Multi_Item_Selection', 'MultiChecks', 'Form']
                                        },
                                    'Adding':
                                        {
                                         'New Bill': ['Table_Selected', 'New', 'Bills'],
                                         'New Vendor' : ['Table_Selected', 'New', 'Vendors'],
                                         'Upload Bill' : ['Single_Item_Selection', 'Upload', 'Source'],
                                         'Upload Payment' : ['Single_Item_Selection', 'Upload', 'Proof']
                                         },

                                    'Editing':
                                        {
                                         'Edit Item' : ['Single_Item_Selection', 'Edit', 'Form'],
                                         'Match': ['Two_Item_Selection', 'Match', ''],
                                         'Accept': ['All_Item_Selection', 'Accept', '']
                                        },

                                    'View Docs':
                                        {
                                         'Bill Source' : ['Single_Item_Selection', 'View', 'Source'],
                                         'Receipt' : ['Single_Item_Selection', 'View', 'Proof'],
                                         'Pay Record' : ['Single_Item_Selection', 'View', 'Check']
                                         },

                                    'Undo':
                                        {
                                          'Delete Item': ['All_Item_Selection', 'Undo', 'Delete'],
                                          'Undo Payment': ['All_Item_Selection', 'Undo', 'Payment']
                                        },
                                    'Tasks':
                                        {
                                          'Detention Report': ['No_Selection_Plus_Display', 'Street_Turn', 'None'],
                                          'Chassis Report': ['No_Selection_Plus_Display', 'Unpulled_Containers', 'None'],
                                          'Bill Calendar' : ['No_Selection_Plus_Display_Plus_Left_Panel_Change', 'Assign_Drivers', 'None']
                                        }

                                    }
                    }

Bills_setup = {'name' : 'Billing',
                'table': 'Bills',
                'filter': None,
                'filterval': None,
                'checklocation': 6,
                'creators': ['Jo'],
                'ukey': 'Jo',
                'simplify': ['Min','ExpType','PayInfo','PayInfo2','Docs'],
                'entry data': [['Jo', 'JO', 'JO', billcode, 'text', 0, 'ok', 'cc', None, 'Always'],
                                ['Date', 'Bill Date', 'Bill Date',  'date', 'date', 0, 'ok', 'cc', None, 'Always'],
                                ['dDate', 'Due Date', 'Due Date',  'date', 'date', 0, 'ok', 'cc', None, 'Always'],
                                ['Company', 'Vendor', 'Select Vendor', 'select', 'vendordata', 0, 'ok', 'cl', 15, 'Always'],
                                ['bAmount', 'Bill$', 'Bill$', 'text', 'float', 0, 'ok', 'cr', None, 'Always'],
                                ['Co', 'Co', 'Co/Div', 'select', 'codata', 0, 'ok', 'cc', None, 'Always'],

                                ['bAccount','ExAcct', 'Pay Acct', 'select', 'expdata', 0, 'ok', 'cl', None, 'ExpType'],
                                ['bType','Ptype', 'Ptype', 'disabled', 'disabled', 0, 'ok', 'cc', None, 'ExpType'],
                                ['bCat', 'D/I', 'D/I', 'disabled', 'disabled', 0, 'ok', 'cl', None, 'ExpType'],
                                ['bSubcat','Cat', 'Cat', 'disabled', 'disabled', 0, 'Category', 'cl', None, 'ExpType'],

                                ['pMeth','Pay Meth', 'Pay Method', 'select', 'paymethods', 0, 'ok', 'cl', None, 'PayInfo'],
                                ['pAccount','Pay Account', 'Paid From Account', 'select', 'acctdata', 0, 'ok', 'cl', None, 'PayInfo'],
                                ['pAmount','Paid Amount', 'Paid Amount', 'text', 'amtpaid', 0, 'ok', 'cr', None, 'PayInfo2'],
                                ['pDate','Paid Date', 'Paid Date', 'date', 'date', 0, 'ok', 'cc', None, 'PayInfo'],
                                ['Description','Desc', 'Desc', 'text', 'text', 0, 'ok', 'cl', None, 'PayInfo'],
                                ['Memo','Memo', 'Check Memo', 'text', 'text', 0, 'ok', 'cl', None, 'PayInfo'],
                                ['Ref','RefNo', 'RefNo or Check#', 'text', 'text', 0, 'ok', 'cl', None, 'PayInfo'],

                               ['Source', 'Bill', 'Source', 'text', None, 0, 'ok', 'cL', None, 'Docs'],
                               ['Proof', 'Pf', 'Proof', 'text', None, 0, 'ok', 'cL', None, 'Docs'],
                               ['Check', 'Ck', 'Check', 'text', None, 0, 'ok', 'cL', None, 'Docs']

                               ],
                'hidden data': [],
                'colorfilter': ['Status'],
                'filteron':  ['Date'],
                'side data': [{'vendordata': ['People', [['Ptype', 'Vendor']], 'Company']},
                              {'acctdata': ['Accounts', [['Type', 'Bank']],'Name']},
                              {'expdata': ['Accounts', [['Co', 'get_Co'],['Type','Expense']], 'Name']},
                              {'codata': ['Divisions', [['Name', 'All']], 'Co']}
                              ],
                'default values': {'get_Co': 'N'},
                'form checks': {
                       'New': ['Date', 'dDate', 'Company', 'bAmount', 'Co', 'bAccount'],
                       'Edit': ['Date', 'dDate', 'Company', 'bAmount', 'Co', 'bAccount'],
                       'MultiChecks': ['Date', 'dDate', 'Company', 'bAmount', 'Co', 'bAccount','pMeth','pAccount','pAmount','pDate','Ref']
                                },
                'form show': {
                                'New': ['ExpType'],
                                'Edit':['ExpType','PayInfo','PayInfo2'],
                                'MultiChecks':['PayInfo']
                                },
                'bring data': [['Bills','bAccount','Accounts','Name',['Name', 'Category', 'Subcategory', 'Type', 'Co'],['bAccount','bCat','bSubcat', 'bType', 'Co']],
                               ['Bills','Company','People','Company',['id'],['Pid']]
                               ],
                'jscript': 'dtTrucking',
                'documents': ['Source', 'Proof', 'Check'],
                'sourcenaming': ['Source_Pay', 'c0', 'Jo'],
                'copyswaps' : {},
                'haulmask' : {},
                'matchfrom':    {
                                },
                'summarytypes': {
                                    'Invoice': {
                                            'Top Blocks': ['Bill To', 'Pickup and Return for Dray Import', 'Deliver To'],
                                            'Middle Blocks': ['Order #', 'BOL #', 'Container #', 'Job Start', 'Job Finished'],
                                            'Middle Items': ['Order', 'Booking', 'Container', 'Date', 'Date2'],
                                            'Lower Blocks': ['JO', 'Gate Out-In', 'In-Booking', 'Container', 'Description/Notes', 'Amt']
                                        }

                                    }
                }

Vendors_setup = {'name' : 'Vendor',
                   'table': 'People',
                   'filter': 'Ptype',
                   'filterval': 'Vendor',
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
                   'haulmask': [],
                   'colorfilter': None,
                    'filteron': [],
                    'side data': [],
                    'default values': {'get_Shipper': 'Fill This Later'},
                    'form show': {
                        'New': [],
                        'Edit': []
                    },
                    'form checks': {
                        'New': ['Company'],
                        'Edit': ['Company']
                    },
                    'jscript': 'dtHorizontalVerticalExample3',
                    'documents': ['Source'],
                    'sourcenaming': [None, None, 'Company'],
                    'copyswaps': {}
                    }
