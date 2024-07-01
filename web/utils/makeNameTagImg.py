from PIL import Image, ImageDraw, ImageFont, ImageOps
import os
from utils.genNameTagDoc import getNameTagSpec


# ------------ this function generates the name tag images and save them in staging directory ---------
def makeNameTagImg(qrFullPathFile, logoPath):

    qrFileName = os.path.basename(qrFullPathFile)
    fname = qrFileName.split(".")    # split filename and ext
    nameOfFile = fname[0]            # get name part

    logoWidth = 627     # 501        # originally 2509, 20% is 501, 25% is 627
    logoHeight = 346    # 276        # orignally 1382, 20% is 276, 25% is 346
    qrWidth = 360                    # originally 450
    qrHeight = 360                   # originally 450
    dmbcRightShift = 150
    nameRightshift = -35   # -ve is to the left of middle  +ve is right of middle
    fnameHOffset = 50      # middle + 50
    lnameHOffset = 180     # middle + 180
    xLogo = -80   # logo is transparent but wide, we have to use -50 as xPos
    yLogo = 30

    NameTagStagingPath, LabelImgW, LabelImgH = getNameTagSpec()     # get paper size, label width and height etc.

    xQr = LabelImgW - 350		    # move to right side, left most is  0
    yQr = LabelImgH - 350			# qr image from bottom of badge
    smallerFontSize = 110
    regFontSize = 120
    # =======================================================================================================
    # Details: Below we
    #          1. created a white background label 'imgBadge' , add borders so we know the boundary
    #          2. paste the Logo and QR Code image at the right place
    #          3. then we created an 'imgLabel' for labeling text into it
    #          4. Finally we create a new 'Blank_image' with name tag size, and paste both 'imgBadge' and
    #             'imgLabel' onto it
    #          5. each page can take 8 labels, so we start a new page when necessary
    #
    # create a badge background
    imgBadgeNoBorder = Image.new(mode="RGBA", size=(LabelImgW, LabelImgH), color="white")
    width, height = imgBadgeNoBorder.size
    imgSmallLogo = Image.open(f"{logoPath}/4RFridayLogo.png").resize((logoWidth, logoHeight), Image.LANCZOS)

    label = qrFileName.split('_')  # file names contain names phone etc.
    firstname = label[1]
    lastname = label[2]

    # ------------------------------------------------------------------------------
    # Important: we need to paste the logo and qrcode before making border, so
    #  that the border will cover the edge of the 'white' border of qr code.
    imgBadgeNoBorder.paste(imgSmallLogo, (xLogo, yLogo), mask=imgSmallLogo)            # paste logo
    # ---------------- also we paste the qrcode at bottom left corner --------------
    imgqr = Image.open(f"{qrFullPathFile}").resize((qrWidth, qrHeight), Image.LANCZOS)
    imgBadgeNoBorder.paste(imgqr, (xQr, yQr), mask=imgqr)                   # paste qr code

    imgBadge = ImageOps.expand(imgBadgeNoBorder, border=20, fill="green")   # add a border for the name tag

    # ----------- now we can write the text: DMBC 4R, first name, last name etc -----
    imgLabel = ImageDraw.Draw(imgBadge)     # create the badge label canvas for us to draw text
    font = ImageFont.truetype('arial.ttf', 80)

    msg = 'DMBC 4R'
    w = imgLabel.textlength(msg, font=font)
    h = font.size                      # textsize is deprecated w,h = draw.textsize(msg, font = font)
    imgLabel.text(((width - w) / 2 + dmbcRightShift, 100), msg, fill=(28, 150, 67), font=font)

    msg = firstname
    if len(firstname) > 7:
        font = ImageFont.truetype('arial.ttf', smallerFontSize)
    else:
        font = ImageFont.truetype('arial.ttf', regFontSize)
    w = imgLabel.textlength(msg, font=font)
    imgLabel.text(((width - w) / 2 + nameRightshift, (height - h) / 2 + fnameHOffset), msg, fill=(0, 0, 0), font=font)

    msg = lastname
    if len(lastname) > 8:
        font = ImageFont.truetype('arial.ttf', smallerFontSize)
    else:
        font = ImageFont.truetype('arial.ttf', regFontSize)
    w = imgLabel.textlength(msg, font=font)

    imgLabel.text(((width - w) / 2 + nameRightshift, (height - h) / 2 + lnameHOffset), msg, fill=(0, 0, 0), font=font)

    imgBadge.save(f"{NameTagStagingPath}/{nameOfFile}_nt.png")     # save the copy in staging
    return 0                                                        # finished making return the BadgeImage
