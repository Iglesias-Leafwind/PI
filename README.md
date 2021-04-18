## Management and recovery of digital images
### Final Project of Informatics Engineering Degree



[TOC]



#### 1. Inception Phase 



##### 1.1 Communications Plan

------

##### **Messaging Platform:** Slack;

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

------

Our [website](http://xcoa.av.it.pt/~pi202021g03/) aims to present the concept of our project, as well as the context and the problem leading to it. It presents our objectives and the main services we wish to implement. The website also contains a section that is constantly being updated with all our deliverables. There is also a team section



##### 1.3 Context

------

In an increasingly digital society, for which the fast technological development of smartphones is not indifferent, allowing to take photos with better quality and less effort, it is essential to manage the entire amount of digital photos in a device.



##### 1.4 Problem

------

When one has to deal with a large number of digital photographs in a device and needs to find that one specific photo - or a group of them -, it is usually a very tedious and unpleasant experience, especially if the photos are badly organized. It's for this very reason that a lot of image search systems are appearing and gaining a lot of attention lately, with a lot of systems already developed and allowing users to search their pictures. Most of them, however, are based on the cloud, and that brings a lot of concerns, especially related to trust and privacy matters.



##### 1.5 Goals

------

It is our main goal to present a solution that tackles the problems discussed above and to enable a good experience for users when looking for photos.

The system should allow users to find pictures based on a similar one or on a string of text.

The system should also be able to identify people and match them to their names, allowing this way of search.

To allow further personalization in the search, users should also be capable of adding their tags to the images, adding more criteria to the search. Besides, they should be able to decide the criteria on the order in which photos will appear.



##### 1.6 Key Functionalities 

------

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

------

At the end of this project, we expect to meet all the proposed objectives and requirements, to have a functional application able to search images through a similar image, to search images by a textual description or tags, such as people, objects or places; the images found should be ordered by relevance, and by given criteria, for example if the client searches for ball, car and bicycle, the result should be ordered so that the first images contain the 3 tags, the next only 2 and the last just 1. Moreover we also hope to have at the end a simple and easy to use user interface.



##### 1.8 Related Work

------

* [Tineye.com](https://tineye.com/ ): reverse image search engine, which means it uses a URL of an image or an image file to search and find similar - or the same - images scattered all around the web
* [Google Images](https://www.google.pt/imghp?hl=pt-PT&ogbl): this tool allows us to search using images or keywords, while giving us many filters to enhance the result list. It's the most famous one, but some competitors browsers have their image search engines too, like Yahoo or Bing
* [Picsearch.com](https://www.picsearch.com/): the difference between this search engine and any other is that it tries to bring a broader variety of pictures around a specific word
* [Flickr](https://flickr.com/): cloud storage based image search engine, which means that we store the images on the site itself and it has its search engine for the images, you can also store it as private or public for anyone to find.



##### 1.9 Team

------

* **Advisor:** [António Neves](https://www.linkedin.com/in/ajrneves/)
* **Co-Advisor:** [Ricadrdo Ribeiro](https://www.linkedin.com/in/ricardo-ribeiro-713b9a135/)
* **Team Manager:** Pedro Iglésias 
* **Product Owner:** [Alexandra de Carvalho](https://www.linkedin.com/in/alexandra-de-carvalho/)
* **Architect Expert #1:** [Mariana Santos](https://www.linkedin.com/in/marspsantos/)
* **Architect Expert #2:** Wei Ye
* **DevOps Master:** [Anthony Pereira](https://www.linkedin.com/in/anth0nypereira/)



##### 1.10 Task List

------

- NLP (Alexandra and Anthony)
- Frontend (Alexandra and Anthony)
- Image to text (Pedro and Mariana)
- BD (Wei and Pedro)
- Search engine(Wei and Mariana)



##### 1.11 Calendar

------

![](project-website/website/img/portfolio/calendar.png)