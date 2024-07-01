from PIL import Image
from math import ceil
import os


def nameTagInit():
    global NameTagStagingPath
    NameTagStagingPath = "./static/nameTagsToPrint"
    global NameTagsDoc
    NameTagsDoc = "./static/nameTagsDoc"
    # ------ variables pertaining only in this file ------------------
    dpi = 300
    global PaperSize
    PaperSize = (int(8.5 * dpi), int(11 * dpi))        # Size of paper to print (8.5x11)
    global LabelImgW, LabelImgH
    LabelImgW = int((PaperSize[0]) / 2.25)           # each row would have 2 labels
    LabelImgH = int((PaperSize[1]) / 4.5)            # 4 rows of labels, add 0.5 for margins


def getNameTagSpec():
    return NameTagStagingPath, LabelImgW, LabelImgH


# =========== utility to print name tags on file, 8 per page ==================
def genNameTagDoc():

    # -------- first get all files in label images statging directory --------
    nameTagImgFiles = [f for f in os.listdir(NameTagStagingPath)]  # get all files
    numNames = len(nameTagImgFiles)         # num(1 for line in open(filename))
    tagsPerPg = 8                           # print 8 tags per page
    numPages = int(ceil(float(numNames) / tagsPerPg))   # get exact pages
    count = 0
    pg = 0
    leftMargin = 80
    gap = 30                                   # gap between each row of labels
    topMargin = 50

    for f in nameTagImgFiles:
        fullpathStagingLabel = f"{NameTagStagingPath}/{f}"
        imgBadge = Image.open(fullpathStagingLabel)               # open the nametag image file
        width, height = imgBadge.size                             # get the with and height
        # imgBadge width, height = makeNameTagImg( f )            # all we do is pass the file name
        yPos = int(count / 2) * (height + gap) + topMargin        # every 2 rows need to add previous tags height
        xPos = (count % 2) * (width + gap) + leftMargin        # every odd name tag is on left, need to add width of tag
        if count == 0:
            blank_image = Image.new("RGB", PaperSize, "White")       # create the new page to begin
            blank_image.paste(imgBadge, (xPos, yPos))                # keep populate 8 name tags
            # blank_image.save(f"{NameTagsDoc}/{count}.pdf",'pdf')      # save 1 for reference
        else:
            blank_image.paste(imgBadge, (xPos, yPos))

        if count == (tagsPerPg - 1):            # done 8 of them, save and next page
            fname = f"{NameTagsDoc}/{pg}.png"
            blank_image.save(fname, 'png')
            pg += 1            # increment page
            count = -1        # reset count to -1

        if pg == numPages - 1 and count == (numNames % tagsPerPg) - 1:
            print("last page ")
            fname = f"{NameTagsDoc}/{pg}.png"                # str(pg)+.png
            blank_image.save(fname, 'png')

        os.remove(fullpathStagingLabel)                    # remove what we have already processed
        count += 1
