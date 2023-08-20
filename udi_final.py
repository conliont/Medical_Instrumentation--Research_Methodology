import requests
import pandas as pd
import tkinter as tk
from tkinter import filedialog
import re
import time
from bs4 import BeautifulSoup


def get_api(udi): # retrieves device information in JSON format and returns the JSON response
    g = requests.get(
        'https://accessgudid.nlm.nih.gov/api/v2/devices/lookup.json?di='+str(udi))    
    return g.json()


def user_input():
    # Dialog box. Enter UDI list excel file
    root = tk.Tk()
    root.withdraw()
    input_file_path = filedialog.askopenfilename(
        filetypes=[('.xlsxfiles', '.xlsx')], title='Select UDI list excel file')
    i = input_file_path.rfind('/')
    # output folder path = input folder path
    output_folder_path = input_file_path[:i + 1]

    df = pd.read_excel(input_file_path, usecols=['Σχόλια'])
    udi_list = df['Σχόλια'].tolist()

    df2 = pd.read_excel(input_file_path, usecols=['Ειδική Ομάδα'])
    udi_list2 = df2['Ειδική Ομάδα'].tolist()

    df3 = pd.read_excel(input_file_path, usecols=['Κατασκευαστής'])
    udi_list3= df3['Κατασκευαστής'].tolist()

    df4 = pd.read_excel(input_file_path, usecols=['Μοντέλο'])
    udi_list4= df4['Μοντέλο'].tolist()

    udis = []
    specific_categories = []
    companyName = []
    brandName = []

    for i in range(0, len(udi_list)):
        companyName.append(udi_list3[i])
        brandName.append(udi_list4[i])
        specific_categories.append(udi_list2[i])
        udis.append(find_14_digit_number(udi_list[i]))

    return udis, output_folder_path, specific_categories, companyName, brandName


def strip_english(string): # find only English terms in specific categories in my excel
    string = re.sub(r"[^A-Za-z]", " ", string.strip())
    words = string.split()    
    return words


def cross_check_words(words, string): # compares a list of words with a string and checks if at least two words from the list are present in the string
    confidence = 0
    for word in words:
        if word in string:
            confidence += 1

    if (confidence > 1): # how many same words
        return True
    else:
        return False


def find_14_digit_number(string): # searches a string for a 14-digit number using a regular expression pattern
    pattern = r'\b\d{14}\b'
    matches = re.findall(pattern, string)    
    return matches


def format(): #initialize my dictionary for storing my data
    error = 0
    Device_Data = {'UDI': [],
                   'Company Name': [],
                   'Brand Name': [],
                   'GMDN Name': [],
                   'GMDN Cross Reference': [],
                   'GMDN Definition': []
                   }
    return error, Device_Data


def make_keywords(items): # make keywords that will by used in advanced search for company name and brand name
    keywords = []
    keywords = strip_english(items)    
    return keywords  # returns a list with the english keywords found in Excel


def search(udi, keywords, descriptions,nonNormalFlag=False): # performs a search based on the provided UDI, keywords, and descriptions
    print('searching: ' + str(udi))
    error, data = format()
    call = get_api(udi)

    if ('error' in call):
        error += 1
        
    elif(nonNormalFlag): # when i have wrong udi
        data['UDI'] = "N/A"
        data['Company Name'] = call['gudid']['device']['companyName']
        data['Brand Name'] = call['gudid']['device']['brandName']
        data['GMDN Name'] = call['gudid']['device']['gmdnTerms']['gmdn'][0]['gmdnPTName']

        if (cross_check_words(keywords, data['GMDN Name'])): 

            data['GMDN Cross Reference'] = "Same"
        else:
            data['GMDN Cross Reference'] = descriptions

        data['GMDN Definition'] = call['gudid']['device']['gmdnTerms']['gmdn'][0]['gmdnPTDefinition']
    else:
        data['UDI'] = udi
        data['Company Name'] = call['gudid']['device']['companyName']
        data['Brand Name'] = call['gudid']['device']['brandName']
        data['GMDN Name'] = call['gudid']['device']['gmdnTerms']['gmdn'][0]['gmdnPTName']
      
        if (cross_check_words(keywords, data['GMDN Name'])): 

            data['GMDN Cross Reference'] = "Same"
        else:
            data['GMDN Cross Reference'] = descriptions

        data['GMDN Definition'] = call['gudid']['device']['gmdnTerms']['gmdn'][0]['gmdnPTDefinition']
        
    return error, data


def search_By_Queries(companyName,model): # performs an advanced search based on company name and brand name
    
    refs = []
    ids = []
    additive = "companyName:("+companyName+")"
    additive += " AND brandName:("+model+")"
    print("searching: " + additive)
    req = requests.get('https://accessgudid.nlm.nih.gov/devices/search?query='+additive) 
    soup = BeautifulSoup(req.content, 'html.parser') 
    soups = soup.find_all("div", {"class": "resultRow no-padding"}) 
    for soup in soups:
        refs.append(soup.find_all("a")) 
    
    for i in range (0, len(refs)):
        te = find_14_digit_number(str(refs[i][0])) 
        if(te!=[]):
            ids.append(te[0])
        else:
            return []
        
    return ids


def cross_ref_by_numbers(ids): # takes a list of device IDs, makes API calls for each ID, and counts the occurrences of GMDN names
    gmdn_names = {}
    for id in ids:
        print(id)
        ref = get_api(id)['gudid']['device']['gmdnTerms']['gmdn'][0]['gmdnPTName'] 
        if ref in gmdn_names:
            gmdn_names[ref][1] += 1
        else:
            gmdn_names[ref]=[id,1]
    k = ""
    i = 0
    for key in gmdn_names:
        
        if (gmdn_names[key][1]>i):
            k = key
            i = gmdn_names[key][1]

    return k,gmdn_names[k][0]



def output(data_dict, dir):
    df = pd.DataFrame(data_dict)  # dataframe containing comparison results
  
    path = dir + '/' + 'udi_checkresults_advanced.xlsx'
   
    with pd.ExcelWriter(path) as engine:
        df.to_excel(excel_writer=engine, index=False)
        

def main():
    
    output_dict = []
    udis, output_dir, categories, companyName, brandName = user_input()
    for i in range(0,len(udis)):
        if (udis[i] == []):
            #continue  # Comment this line for Advanced Search
                
            ids = search_By_Queries(companyName[i],brandName[i])
            if (ids == []):
                pass
            else:
                key,id = cross_ref_by_numbers(ids)
                er, D = search(id,make_keywords(brandName[i]),categories[i],True)
                
        else:
            er, D = search(udis[i][0], make_keywords(categories[i]), categories[i])
        time.sleep(0.1)

        if er == 0:
            output_dict.append(D)

    output(output_dict, output_dir)


main()
