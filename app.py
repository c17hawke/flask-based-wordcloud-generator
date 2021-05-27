'''
# Author: Sunny Bhaveen Chandra
# Contact: sunny.c17hawke@gmail.com
# dated: March, 04, 2020
'''
# import necessary libraries
from bs4 import BeautifulSoup as soup
import urllib
import requests
import pandas as pd
import time
import os
from flask import Flask, render_template,  session, redirect, request
from flask_cors import CORS,cross_origin
import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS
import ssl

# define global paths for Image and csv folders
IMG_FOLDER = os.path.join('static', 'images')
CSV_FOLDER = os.path.join('static', 'CSVs')

app = Flask(__name__)
cors = CORS(app, resources={r"/api/*": {"origins": "*"}})
# config environment variables
app.config['IMG_FOLDER'] = IMG_FOLDER
app.config['CSV_FOLDER'] = CSV_FOLDER

# ssl certificate verification 
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    # Legacy Python that doesn't verify HTTPS certificates by default
    pass
else:
    # Handle target environment that doesn't support HTTPS verification
    ssl._create_default_https_context = _create_unverified_https_context
	
class DataCollection:
	'''
	class meant for collection and management of data
	'''
	def __init__(self):
		# dictionary to gather data
		self.data = {"Product": list(), 
		"Name": list(),
		"Price (INR)": list(), 
		"Rating": list(), 
		"Comment Heading": list(), 
		"Comment": list()}

	def get_final_data(self, commentbox=None, prodName=None, prod_price=None):
		'''
		this will append data gathered from comment box into data dictionary
		'''
		# append product name
		self.data["Product"].append(prodName)
		self.data["Price (INR)"].append(prod_price)
		try:
			# append Name of customer if exists else append default
			self.data["Name"].append(commentbox.div.div.\
				find_all('p', {'class': '_2sc7ZR _2V5EHH'})[0].text)
		except:
			self.data["Name"].append('No Name')

		try:
			# append Rating by customer if exists else append default
			self.data["Rating"].append(commentbox.div.div.div.div.text)
		except:
			self.data["Rating"].append('No Rating')

		try:
			# append Heading of comment by customer if exists else append default
			self.data["Comment Heading"].append(commentbox.div.div.div.p.text)
		except:
			self.data["Comment Heading"].append('No Comment Heading')

		try:
			# append comments of customer if exists else append default
			comtag = commentbox.div.div.find_all('div', {'class': ''})
			self.data["Comment"].append(comtag[0].div.text)
		except:
			self.data["Comment"].append('')	

	def get_main_HTML(self, base_URL=None, search_string=None):
		'''
		return main html page based on search string
		'''
		# construct the search url with base URL and search string
		search_url = f"{base_URL}/search?q={search_string}"
		# usung urllib read the page
		with urllib.request.urlopen(search_url) as url:
			page = url.read()
		# return the html page after parsing with bs4
		return soup(page, "html.parser")

	def get_product_name_links(self, flipkart_base=None, bigBoxes=None):
		'''
		returns list of (product name, product link)
		'''
		# temporary list to return the results
		temp = []
		# iterate over list of bigBoxes
		for box in bigBoxes:
			try:
				# if prod name and list present then append them in temp
				temp.append((box.div.div.div.a.img['alt'],
					flipkart_base + box.div.div.div.a["href"]))
			except:
				pass
			
		return temp

	def get_prod_HTML(self, productLink=None):
		'''
		returns each product HTML page after parsing it with soup
		'''
		prod_page = requests.get(productLink)
		return soup(prod_page.text, "html.parser")


	def get_data_dict(self):
		'''
		returns collected data in dictionary
		'''
		return self.data

	def save_as_dataframe(self, dataframe, fileName=None):
		'''
		it saves the dictionary dataframe as csv by given filename inside
		the CSVs folder and returns the final path of saved csv
		'''
		# save the CSV file to CSVs folder
		csv_path = os.path.join(app.config['CSV_FOLDER'], fileName)
		fileExtension = '.csv'
		final_path = f"{csv_path}{fileExtension}"
		# clean previous files -
		CleanCache(directory=app.config['CSV_FOLDER'])
		# save new csv to the csv folder
		dataframe.to_csv(final_path, index=None)
		print("File saved successfully!!")
		return final_path


	def save_wordcloud_image(self, dataframe=None, img_filename=None):
		'''
		it generates and saves the wordcloud image into wc_folder
		'''
		# extract all the comments
		txt = dataframe["Comment"].values
		# generate the wordcloud
		wc = WordCloud(width=800, height=400, background_color='black', stopwords=STOPWORDS).generate(str(txt))

		plt.figure(figsize=(20,10), facecolor='k', edgecolor='k')
		plt.imshow(wc, interpolation='bicubic') 
		plt.axis('off')
		plt.tight_layout()
		# create path to save wc image
		image_path = os.path.join(app.config['IMG_FOLDER'], img_filename + '.png')
		# Clean previous image from the given path
		CleanCache(directory=app.config['IMG_FOLDER'])
		# save the image file to the image path
		plt.savefig(image_path)
		plt.close()
		print("saved wc")


class CleanCache:
	'''
	this class is responsible to clear any residual csv and image files
	present due to the past searches made.
	'''
	def __init__(self, directory=None):
		self.clean_path = directory
		# only proceed if directory is not empty
		if os.listdir(self.clean_path) != list():
			# iterate over the files and remove each file
			files = os.listdir(self.clean_path)
			for fileName in files:
				print(fileName)
				os.remove(os.path.join(self.clean_path,fileName))
		print("cleaned!")

# route to display the home page
@app.route('/',methods=['GET'])  
@cross_origin()
def homePage():
	return render_template("index.html")

# route to display the review page
@app.route('/review', methods=("POST", "GET"))
@cross_origin()
def index():
	if request.method == 'POST':
		try:
			# get base URL and a search string to query the website
			base_URL = 'https://www.flipkart.com' # 'https://www.' + input("enter base URL: ")
			
			# enter a product name eg "xiaomi"
			# search_string = input("enter a brandname or a product name: ")
			search_string = request.form['content']
			
			# fill the spaces between seA caption for the above image.arch strings with +
			search_string = search_string.replace(" ", "+")
			print('processing...')

			# start counter to count time in seconds
			start = time.perf_counter()

			get_data = DataCollection()

			# store main HTML page for given search query
			flipkart_HTML = get_data.get_main_HTML(base_URL, search_string)

			# store all the boxes containing products
			bigBoxes = flipkart_HTML.find_all("div", {"class":"_1AtVbE col-12-12"})

			# store extracted product name links
			product_name_Links = get_data.get_product_name_links(base_URL, bigBoxes)

			# iterate over product name and links list
			for prodName, productLink in product_name_Links[:4]:
				# iterate over product HTML
				for prod_HTML in get_data.get_prod_HTML(productLink):
					try:
						# extract comment boxes from product HTML
						comment_boxes = prod_HTML.find_all('div', {'class': '_16PBlm'}) #_3nrCtb

						prod_price = prod_HTML.find_all('div', {"class": "_30jeq3 _16Jk6d"})[0].text
						prod_price = float((prod_price.replace("₹", "")).replace(",", ""))
						# iterate over comment boxes to extract required data
						for commentbox in comment_boxes:
							# prpare final data
							get_data.get_final_data(commentbox, prodName, prod_price)
							
					except:
						pass

			# save the data as gathered in dataframe
			df = pd.DataFrame(get_data.get_data_dict())

			# save dataframe as a csv which will be availble to download
			download_path = get_data.save_as_dataframe(df, fileName=search_string.replace("+", "_"))

			# generate and save the wordcloud image
			get_data.save_wordcloud_image(df, 
			img_filename=search_string.replace("+", "_"))

			# finish time counter and calclulate time taked to complet ethis programe
			finish = time.perf_counter()
			print(f"program finished with and timelapsed: {finish - start} second(s)")
			return render_template('review.html', 
			tables=[df.to_html(classes='data')], # pass the df as html 
			titles=df.columns.values, # pass headers of each cols
			search_string = search_string, # pass the search string
			download_csv=download_path # pass the download path for csv
			)
		except Exception as e:
			print(e)
			# return 404 page if error occurs 
			return render_template("404.html")

	else:
		# return index page if home is pressed or for the first run
		return render_template("index.html")

# route to display wordcloud
@app.route('/show')  
@cross_origin()
def show_wordcloud():
	img_file = os.listdir(app.config['IMG_FOLDER'])[0]
	full_filename = os.path.join(app.config['IMG_FOLDER'], img_file)
	return render_template("show_wc.html", user_image = full_filename)

if __name__ == '__main__':
	app.run(debug=True)
