## Management and recovery of digital images
### Final Project of Informatics Engineering Degree

#### How to install

**Install:**
* **Python:**
	* https://www.python.org/downloads/release/python-380/
* **JDK 11:**
	* https://www.oracle.com/pt/java/technologies/javase-jdk11-downloads.html
* **or:**
	* https://jdk.java.net/java-se-ri/11
* **Cmake:**
	* https://cmake.org/download/
**Create venv:**
* **Windows:**
	* python -m venv venv
	* activate venv
	* pip install -r requirements.txt
**Startup system:**
* **Executable:**
	* Just double click
* **Python File:**
	* python Imageable.py
* **or while in venv:**
	* python Initialize.py

#### Known issues:
* **JDK works between versions 11 and 15**
* **Problems with neo4j or elasticsearch not finding java**
	* **Setup JAVA_HOME as a environment variable:**
	* **Windows:**
		* Locate your Java installation directory (probably: C:\Program Files\Java\jdk11)
		* ** Windows 7**
			* Right click My Computer and select Properties > Advanced
		* ** Windows 8**
			* Go to Control Panel > System > Advanced System Settings
		* ** Windows 10**
			* Search for Environment Variables then select Edit the system environment variables
		* Click the Environment Variables button.
		* Under System Variables, click New.
		* In the Variable Name field, enter:
		* **JAVA_HOME**
		* In the Variable Value field enter:
		* **DK installation path (probably: C:\Program Files\Java\jdk11)**
		* Click OK and Apply Changes as prompted
	* **Linux:**
		* Open Console
		* Make sure you have installed Java already
		* Execute: vi ~/.bashrc OR vi ~/.bash_profile
		* add line : export JAVA_HOME=/usr/java/jdk11
		* save the file.
		* source ~/.bashrc OR source ~/.bash_profile
		* Execute : echo $JAVA_HOME
		* Output should print the path /usr/java/jdk11

[TOC]



#### 1. Inception Phase 



##### 1.1 Communications Plan

**Messaging Platform:** Slack;

* **Standards:**
  * Each milestone has a separate channel to discuss deliverables 
  * Each ongoing work module has its separate channel
  * A separate channel for scheduling meetings
  * A separate channel for discussing milestone powepoint presentations

**Video Conference Platform:** Zoom;

**Code Repository:** [Github](https://github.com/my-life-ua/mylife#19-communication-plan)

* **Standards:**
  * Master branch is only pushed by the DevOps Master at the end of each milestone
  * Develop branch diverges from Master, and is often updated through pull requests, revised and merged by the DevOps Master
  *  All new features have their own branch `feature/feature-name`, and they all diverge from Develop
  * All fixes have their own branch `hotfix/fix-name`

**Backlog Management:** [Jira](https://alexandradecarvalho.atlassian.net/secure/RapidBoard.jspa?rapidView=1&projectKey=PI)

**Shared Documents Repository:** [Confluence](https://alexandradecarvalho.atlassian.net/wiki/spaces/PI/overview)



##### 1.2 Website 

Our [website](http://xcoa.av.it.pt/~pi202021g03/) aims to present the concept of our project, as well as the context and the problem leading to it. It presents our objectives and the main services we wish to implement. The website also contains a section that is constantly being updated with all our deliverables. There is also a team section



##### 1.3 Context

In an increasingly digital society, for which the fast technological development of smartphones is not indifferent, allowing to take photos with better quality and less effort, it is essential to manage the entire amount of digital photos in a device.



##### 1.4 Problem

When one has to deal with a large number of digital photographs in a device and needs to find that one specific photo - or a group of them -, it is usually a very tedious and unpleasant experience, especially if the photos are badly organized. It's for this very reason that a lot of image search systems are appearing and gaining a lot of attention lately, with a lot of systems already developed and allowing users to search their pictures. Most of them, however, are based on the cloud, and that brings a lot of concerns, especially related to trust and privacy matters.



##### 1.5 Goals

It is our main goal to present a solution that tackles the problems discussed above and to enable a good experience for users when looking for photos.

The system should allow users to find pictures based on a similar one or on a string of text.

The system should also be able to identify people and match them to their names, allowing this way of search.

To allow further personalization in the search, users should also be capable of adding their tags to the images, adding more criteria to the search. Besides, they should be able to decide the criteria on the order in which photos will appear.



##### 1.6 Key Functionalities 

As mentioned above, the main functionalities will be:

- Search for similar images
  - that is, for example, given an image of cats, the system should return a list of images related to cats.
- Search images by text
  - is a search that involves natural language processing (NLP), which consists in transforming a description given by a client into more intuitive tags. For example, transforming "eat" into "food".
- Manually add new tags to an image 
  - the client can add new tags to an image he likes.
- Sort and filter results by relevance, and other criteria
  - if client searches ball, car and bike, the result should be ordered so that the first images contain the 3 tags, the next only 2 and the last just 1.



##### 1.7 Expected Results

At the end of this project, we expect to meet all the proposed objectives and requirements, to have a functional application able to search images through a similar image, to search images by a textual description or tags, such as people, objects or places; the images found should be ordered by relevance, and by given criteria, for example if the client searches for ball, car and bicycle, the result should be ordered so that the first images contain the 3 tags, the next only 2 and the last just 1. Moreover we also hope to have at the end a simple and easy to use user interface.



##### 1.8 Related Work

* [Tineye.com](https://tineye.com/ ): reverse image search engine, which means it uses a URL of an image or an image file to search and find similar - or the same - images scattered all around the web
* [Google Images](https://www.google.pt/imghp?hl=pt-PT&ogbl): this tool allows us to search using images or keywords, while giving us many filters to enhance the result list. It's the most famous one, but some competitors browsers have their image search engines too, like Yahoo or Bing
* [Picsearch.com](https://www.picsearch.com/): the difference between this search engine and any other is that it tries to bring a broader variety of pictures around a specific word
* [Flickr](https://flickr.com/): cloud storage based image search engine, which means that we store the images on the site itself and it has its search engine for the images, you can also store it as private or public for anyone to find.



##### 1.9 Team

* **Advisor:** [António Neves](https://www.linkedin.com/in/ajrneves/)

* **Co-Advisor:** [Ricadrdo Ribeiro](https://www.linkedin.com/in/ricardo-ribeiro-713b9a135/)
* **Team Manager:** Pedro Iglésias 
* **Product Owner:** [Alexandra de Carvalho](https://www.linkedin.com/in/alexandra-de-carvalho/)
* **Architect Expert #1:** [Mariana Santos](https://www.linkedin.com/in/marspsantos/)
* **Architect Expert #2:** Wei Ye
* **DevOps Master:** [Anthony Pereira](https://www.linkedin.com/in/anth0nypereira/)



##### 1.10 Task List

* NLP (Alexandra and Anthony)

- Frontend (Alexandra and Anthony)
- Image to text (Pedro and Mariana)
- BD (Wei and Pedro)
- Search engine(Wei and Mariana)



##### 1.11 Calendar

##### ![](project-website/website/img/portfolio/calendar.png)



#### 2. Elaboration Phase

##### 2.1 Actors

- A general user who would like to see his photos organized

##### 2.2 Personas, Scenarios and User Stories

![](project-website/website/img/portfolio/personas/antonio.png)

* **Scenario**

An 84-year-old man, António has worked hard all his life. He lives in Oporto, his homeland, and is looking forward to the dinner he will offer to his youngest grandson, Tomás, in celebration of his admission to college. António prepared a surprise for his son António and grandson Tomás: he was taking pictures of the old albums he had kept in the attic of his house, picking up mold, to ensure that these memories are never lost for all eternity. Thus, António plans to show his grandson photographs of his father, at the same young age - so that everyone remembers that life is an endless cycle.

António wishes to be able to filter the photographs without much difficulty, as he does not have great technological literacy, through a simple interface that allows him to have constant feedback, namely through the appearance of messages with a font size that does not tire his eyes. He should also be able, using face recognition technology and when taking a picture of his son António, to collect all the photos of his son that are in the folder that is being analysed.

* **User story**

As António, I want to be able to filter the photographs without much difficulty, recurring to face recognition, so that I can make a special surprise for my grandson.



![](/home/alexis/Desktop/Licenciatura/3ano2sem/PI/project-website/website/img/portfolio/personas/filipe.png)

* **Scenario**

Filipe is a 25-year-old young man. He took a Representation course, where he quickly caught the attention of national producers. He was part of the soap opera “A Casa Das Sete Donzelas”, in which, being one of the protagonists, he gained national fame. Filipe is in a relationship with Rita, a 26-year-old woman with whom he made a romantic pair in the soap opera in which they both became famous. They married last year in Taipu de Fora, Bahia - an unforgettable moment, according to them. For the celebration of their first anniversary, they intend to make a compilation of the best moments and backstage of their wedding to be published on the social network Instagram, in the account shared by the couple and in which they are supported by a large legion of fans. That’s why, Filipe and Rita intend to filter the photographs they have by location, thus obtaining all the incredible moments that passed on that beach in Brazil.

Filipe and Rita intend to use an easy-to-use application, thus being very intuitive, so that they can filter by a specific location.

* **User story**

As Filipe, I want to filter my photos by location, so that I can make a great compilation of moments from my wedding and share it with my fans.



![](/home/alexis/Desktop/Licenciatura/3ano2sem/PI/project-website/website/img/portfolio/personas/alexa.png)

* **Scenario**

Alexandra is a 21-year-old girl. She decides to enter Veterinary Medicine, where she can do her best to protect all animals. In parallel, she starts volunteering at the animal association “Senhores Bichinhos” in Vila Nova de Gaia, where she takes care of the cats that are in the shelter and holds adoption sessions. In charge of preparing leaflets to advertise the kittens that are in the shelter, in order to be published on the social media Facebook and Instagram, Alexandra intends to use the application in order to filter her photographs to obtain those of a specific cat.

Alexandra intends to use an easy-to-use application that allows her to search for the name of a specific cat from the refuge.

* **User story**

As Alexandra, I want to search for the name of a specific cat from the refuge so that I can make leaflets and share them on social media.





![](/home/alexis/Desktop/Licenciatura/3ano2sem/PI/project-website/website/img/portfolio/personas/jca.png)



* **Scenario**

A 43-year-old man, he lives in the city that saw him came to life and grow, Ovar. He started by studying Architecture Faculdade de Belas Artes, but dropped out of the course a few months later. He later entered Photography at Universidade Lusófona and, having completed his degree, opened a studio of his name - Estúdio Almeida - on the main avenue of the city of Ovar. Approaching the start of the new edition of Viagem Medieval em Terras de Santa Maria, an annual event held in the municipality of Feira around the castle where events and traditions of the Middle Ages are recreated, José intends to advertise photographs of medieval-themed weddings in which he participated in the showcase of his studio. So, having a photo of a medieval wedding, he intends to use the application to find similar images.

José Carlos is looking for an application that is easy to use and that is quick to perform its necessary functions in a vast cluster of photographs, in order to be able, through a photo indicated by him, to find all the related ones that are in the folder that is being used and inspected.

* **User story**

As José, I want to get all photos similar to one indicated by me, so that I can decorate my showcase.





![](/home/alexis/Desktop/Licenciatura/3ano2sem/PI/project-website/website/img/portfolio/personas/viviana.png)

* **Scenario**

Viviana is a 20-year-old student of Business Relations at the University of Coventry, England. She used to spend her summer holidays in Portugal, taking the opportunity to see her family and friends again. An unconditional fan of summer festivals, she used to attend Vodafone Paredes de Coura every year, accompanied by a group of friends. According to her, more than watching the concerts of her favourite artists, it was the coexistence with different people in the accompaniment that made the stay memorable. The barbecues, the conversations around the bonfire in the moonlight, the singing until dawn, everything was recorded in her memory. In times of pandemic, Viviana will not be able to leave England and appear at Vodafone Paredes de Coura for the first time. Feeling nostalgic, she decides to recall the moments experienced in previous editions. Thus, she uses the application to search for the images of the festival, and tries to edit them in order to identify the specific edition in which they were taken.

Viviana hopes to find an easy-to-use application that is intuitive and that supports a large number of photographs, in order to be able to edit each photo and tag the name of the festival and the year in which it was taken.

* **User story**

As Viviana, I want to edit manually each photo, adding the name of the festival and the year in which it was taken, so that I can remember all the good times I spent.



##### 2.3 Use Cases Diagram



![](/home/alexis/Desktop/Licenciatura/3ano2sem/PI/project-website/website/img/portfolio/diagrams/use_case.png)



##### 2.4 State of The Art

* **Google photos**

The service automatically analyzes photos, identifying various visual features and subjects. Users can search for anything in photos, with the service returning results from three major categories: People, Places, and Things. The [computer vision](https://en.wikipedia.org/wiki/Computer_vision) of Google Photos recognizes faces (not only those of humans, but pets as well), grouping similar ones together (this feature is only available in certain countries due to privacy laws); geographic landmarks (such as the [Eiffel Tower](https://en.wikipedia.org/wiki/Eiffel_Tower)); and subject matter, including birthdays, buildings, animals, food, and more.
Different forms of [machine learning](https://en.wikipedia.org/wiki/Machine_learning) in the Photos service allow [recognition](https://en.wikipedia.org/wiki/Object_recognition) of photo contents, automatically generate albums, animate similar photos into quick videos, surface past memories at significant times, and improve the quality of photos and videos

Utilizing the Optical Character **Recognition** (OCR) tech found in **Google** Lens, you can now search for text from within **Google Photos**. Once it finds any **images** that contain that text, you're able to use Lens to select and copy it in order to paste it elsewhere.

It also uses Vision AI which is a machine learning program that using photos and training models it can learn how to identify certain things in the photos.



* **Amazon Photos**

Amazon photos uses a thing called amazon recognition that is able to recognize scenery, object and their tags and it also allows to implement personalized tags. It as text recognition and inappropriate photos filtration. Also it recognizes faces and identifies their expression based on their eyes,mouth. Amazon photos uses media2cloud as a solution for transportation of images to the cloud. **Amazon SageMaker Ground Truth** is a labeling training program where you create a custom label and train it to automatically label what you want. Their database is Amazon dynamoDB that is a key-value and document dbs. Amazon also has its own elastic search called **Amazon Elasticsearch Service.**

**Media Insights Engine** (MIE) is a development framework for building serverless applications that process video, images, audio, and text on AWS. **Operators** are generated state machines that call AWS Lambda functions to perform media analysis or media transformation tasks. Users can define custom operators, but the MIE operator library includes the following pre-built operators: Celebrity Recognition, Content Moderation, Face Detection, Face Search, Label Detection, Person Tracking, Shot Detection, Text Detection, Technical Cue Detection, Comprehend Key Phrases, Comprehend Entities, Create SRT Captions, Create VTT Captions, Media Convert, Media Info, Polly, Thumbnail, Transcribe and Translate.



* **Loggy**

Our work will be similar to Loggy that is being worked on at the moment by Ricardo Ribeiro. 

The work is based on recording the life of a person via smartwatch, wearable cameras, sensors and many other technologies and this data is filtered and processed in the cloud as images. Then we reach the closest to our work, the organizing and filtering of images. And currently, the State-of-the-art approaches in this area have already reached a good performance for detecting/recognizing objects using deep learning approaches, generally Convolutional neural networks (ConvNets). 

The following technologies were investigated for loggy and some of them we are currently being investigating: ImageNet Large Scale Visual Recognition Challenge, Microsoft COCO - Common Objects in Context, some ConvNet architectures such as the VGG, RestNet, Inception, ResNeXt, and EfficientNet, some scenery recognizers such as MIT Indoor 67, SUN - Scene categorization benchmark dataset and Places - Image database for scene recognition.

In this work, the contribution will be to train a scene recognition model adapting a state-of-the-art architecture from object classification, such as EfficientNet or ResNeXt. The mentioned datasets will be used to create a more complete dataset for training the scene recognition model. For example, Places365 dataset contains too many images in categories that are not part of them and consequently can affect the efficiency of the trained model.

The Loggy web application was divided into different modules:

 • Upload of multiple images into the database;

 • Pre-processing the images using ConvNet pre-trained models on the three datasets, such as ImageNet, Microsoft COCO and Places365;

 • Analyse the extracted content and show the results into statistical charts

 • Visualization and summarization into image categories based on the date, scenes, environment and objects.

 

##### 2.5 Requirements 

###### 	2.5.1 Requirements Gathering

We gathered the requirements for our project through brainstorms and analysis of their results with our advisors. We also analyzed the state of the art to extract some important features.

###### 	2.5.2 Functional Requirements

* Find images using text.

* Add image folders for processing.

* Find images using images.

* Facial Recognition in images.

* Object detection in images.

* Image pattern detection.

* Create, assign and delete tags for and from images.

* Filter images by tags.



###### 	2.5.2 Non-Functional Requirements

* Software must be compatible between OSs without creating problems.

* Always available in offline mode.

* Only the current pc user may access the images submitted by that user.

* The users may add password protection for the application.

* The app needs to handle a large amount of processing images at the same time.

* When searching with text on > 100 000 images we must assure that the app takes around 5 seconds.

* When searching with an image on > 100 000 images we must assure that the app takes around 8 seconds.

* It should register if there is an incorrect password attempt and if there is any error that occurred.

* It should warn the user in case there is an error while processing an image.

* In case of an error that can be avoided it should be easily fixed without the user even knowing.



##### 2.6 Technologies Used

###### 	2.6.1 Natural Language Processing Module

NLTK

- free open-source library
- it's considered the main NLP library
- it provides easy-to-use interfaces to over 50 corpora and lexical resources such as Wordnet, a large English dictionary
- some of its features include tokenization, stemming, part-of-speech tagging, lemmatization, named entity recognition, ...

###### 	2.6.1 Image Object Extraction Module

ImageAI

* Python library 
* Returns a list of objects that are in an image
* It is used a RetinaNet model
* Pre-trained with COCO dataset

###### 	2.6.1 Facial Recognition Module

"face_recognition"

*  Wrapper for the facial regocnition functionality
* This library allows training the relationship between a face and a corresponding name through several pictures

###### 	2.6.1 Places365

###### 	2.6.1 Tesseract OCR

###### 	2.6.1 ElasticSearch

##### 2.7 Architecture Diagram



![](project-website/website/img/portfolio/diagrams/arch.png)



##### 2.8 Domain Model

![](project-website/website/img/portfolio/diagrams/model.png)