import PyPDF2
import re
import camelot
import matplotlib.pyplot as plt
import pandas as pd
import tqdm
import os
import pickle

# Replace 'file_path' with the actual path to your PDF file
file_path = r""

#find all pdfs in the folder
pdfs = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.pdf')]

# change this to True to plot the PDF and you should be able to see the coordinates
# of the table(s) you want to extract
if False:
    tables = camelot.read_pdf(
        file_path, 
        flavor='stream', 
        table_regions=['32,518,315,30'],
        pages='1')

    #plot the table
    camelot.plot(tables[0], kind='textedge').show()
    input("")
    exit(0)


AllStatements = pd.DataFrame(columns=['Date', 'Description', 'Out', 'In', 'Balance'])

allcsv = pd.DataFrame(columns=['Date', 'Description', 'Out', 'In', 'Balance'])

# Extract the text from the PDF
for statement in pdfs:
    #get the year
    year = re.search(r'(\d{4})', statement).group(1)
    print(year)
    #extract from first page
    tables = camelot.read_pdf(
        statement, 
        flavor='stream', 
        table_areas=['32,518,421,30'],
        columns=['32,78,263,300,367'])

    
    #find the number of pages
    with open(statement, 'rb') as f:
        pdf = PyPDF2.PdfFileReader(f)
        num_pages = pdf.getNumPages()

    #extract all tables from the other pages
    otherTables = camelot.read_pdf(
        statement, 
        flavor='stream', 
        table_areas=['41,700,428,30'],
        columns=['50,85,264,304,357'],
        pages = ",".join([str(i) for i in range(2, num_pages-1)]))

    
    #convert to a dataframe
    table = tables[0].df
    i = 0
    for t in otherTables:
        table = pd.concat([table, t.df])

    #set the column names
    table.columns = ['', 'Date', 'Description', 'Out', 'In', 'Balance']

    #drop the first column
    table.drop(columns=[''], inplace=True)

    #set the index to the row number
    table.reset_index(inplace=True)

    #add raw to the csv
    allcsv = pd.concat([allcsv, table])
    #save the csv
    allcsv.to_csv('raw.csv')

    #iterate through the rows
    for i, row in table.iterrows():
        #check if it has the header 
        if 'date'.lower() in row['Date'].lower():
            table.drop(i, inplace=True)
            continue

        if year.lower() in row['Date'].lower():
            table.drop(i, inplace=True)
            continue

        if 'description'.lower() in row['Description'].lower():
            table.drop(i, inplace=True)
            continue

        if 'Balance from' in row['Description']:
            table.drop(i, inplace=True)
            continue

        if 'out'.lower() in row['Out'].lower():
            table.drop(i, inplace=True)
            continue
            
        if 'in'.lower() in row['In'].lower():
            table.drop(i, inplace=True)
            continue
            
        if 'balance'.lower() in row['Balance'].lower():
            table.drop(i, inplace=True)
            continue

    for i, row in table.iterrows():
        #checking for correct data
        date = row['Date']
        if date != '':
            date_num = date.split(' ')[0]
            if not date_num.isdigit():
                print(f"Date is not a number: {date_num}")
                print(f"Failed on pdf {statement}")
                exit(0)
            row['Date'] = row['Date'] + ' ' + year
            #update the date
            table.loc[i, 'Date'] = row['Date']

    for i, row in table.iterrows():
        row['Out'] = row['Out'].replace(' ', '').replace(',', '.')
        row['In'] = row['In'].replace(' ', '').replace(',', '.')
        
        if row['Out'] == '':
            #if out is blank, and 'in' is also blank, the description is probably split over multiple lines
            if row['In'] == '':
                #combine the description with the row above, if it doesnt exist, then add to the previous row
                # this is a bit hacky, but im being lazy
                try:
                    table.loc[i-1, 'Description'] = table.loc[i-1, 'Description'] + ' ' + row['Description']
                except:
                    try:
                        table.loc[i-2, 'Description'] = table.loc[i-2, 'Description'] + ' ' + row['Description']
                    except:
                        table.loc[i-3, 'Description'] = table.loc[i-3, 'Description'] + ' ' + row['Description']
                #drop the row
                table.drop(i, inplace=True)
                continue
        else:
            try:
                out = float(row['Out'])
                row['Out'] = out
                #update the row
                table.loc[i, 'Out'] = row['Out']
            except:
                print(f"out is not a number: {row['Out']}")
                print(f"Failed on pdf {statement}")
                exit(0)
        
    #add the statement to the dataframe
    AllStatements = pd.concat([AllStatements, table])

#Pickle the dataframe
with open('AllStatements.pkl', 'wb') as f:
    pickle.dump(AllStatements, f)

#save the csv
AllStatements.to_csv('AllStatements.csv')
