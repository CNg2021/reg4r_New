# ============ generate QR codes for each clients ============
# import modules
import qrcode
from PIL import Image, ImageDraw, ImageFont       # pip install Pillow to get this light weight image processing package
import glob
import os   # ---- for deletion of files in removeQRImg()
from utils.makeNameTagImg import makeNameTagImg


def qrInit():
    global LogoPath
    LogoPath = './static/img'
    global QrcodePath
    QrcodePath = "./static/qrCodeImgs"


# ----------- function to make QR code for user based on id, fname, lname and phone ----------
def genQRCode(id, firstName, lastName, phoneNum):
    # taking image which user wants in the QR code center
    # print (os.getcwd())
    # ====> strToGen = "DMBC4R 0005 David Leung 416-222-4444"

    strToGen = f"DBMC4R {id} {firstName} {lastName} {phoneNum}"
    logo = Image.open(f"{LogoPath}/DMBCLogo.png")
    # taking base width
    basewidth = 120

    # adjust image size
    wpercent = (basewidth / float(logo.size[0]))
    hsize = int((float(logo.size[1]) * float(wpercent)))
    logo = logo.resize((basewidth, hsize), Image.LANCZOS)
    try:
        QRcode = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
        # adding URL or text to QRcode
        QRcode.add_data(strToGen)
        # generating QR code
        QRcode.make()

        # taking color name from user
        QRcolor = 'black'

        # adding color to QR code
        QRimg = QRcode.make_image(fill_color=QRcolor, back_color="white").convert('RGBA')

        # Apr 14,2024 decided to skip logo embedding as it does not require on name tag label
        # pos = ((QRimg.size[0] - logo.size[0]) // 2,
        #     (QRimg.size[1] - logo.size[1]) // 2)
        # QRimg.paste(logo, pos)

        # ------- Mar 18, 2024 try to add a name label to the image ------------
        ImageDraw.Draw(QRimg)
        # Custom font style and font size
        # myFont = ImageFont.truetype('./static/ttf/FTLTLT.TTF', 35)
        # labelImg.text((100,2), f"{id}-{firstName} {lastName} ", font=myFont, fill=(255,0,0) )
        # save the QR code generated
        QRimg.resize((100, 100))    # shrink whole image
        fname = f"{QrcodePath}/{id}_{firstName}_{lastName}_{phoneNum}.png"
        QRimg.save(fname)
        print('QR code generated!')
        # gen the nametag image as well
        makeNameTagImg(fname, LogoPath)
        return fname

    except Exception as err:
        print(f"gen qrcode error {err}")
        return None


# ===================== remove qr code imagea with client removal ==============
# this function is called by deleteClient Only
# ==============================================================================
def removeQRImg(id):
    fileToDelete = f"{QrcodePath}/{id}_*.png"   # we don't need the name

    try:
        for f in glob.glob(fileToDelete):
            os.remove(f)

    except Exception as err:    # we don't really care if file not found
        print(f"remove file error {err}")

    return
