# ----------- Database definitions and functions ---------
# from flask_sqlalchemy import SQLAlchemy
# from sqlalchemy import exc, text, select
#  Mar 25, 2024, after studying the postgresql functions and how to obtain result sets,
#  I decided it's way too patchy and decided to stay with dynamic queries

import psycopg2
import psycopg2.extras
from datetime import date, datetime
from utils.qrGen import genQRCode, removeQRImg
from utils.makeNameTagImg import makeNameTagImg


# ----------- make connector to postgres database -------------
def openPostgresConnection():
    global conn
    conn = psycopg2.connect(database="DMBC4R",
                            user="postgres",
                            password="0453agape",
                            host="db",
                            port="5432",
                            cursor_factory=psycopg2.extras.RealDictCursor)
    if conn:
        print("connected to postgres")


#  *******************************************************************************
#       CLIENT FORM display function
#  *******************************************************************************
#  --------- populate select dropdown field from static table FavActvities -------
def getListOfActivity():
    # cursor= db.session.execute(text( 'SELECT actID, actName FROM activity'))
    try:
        curObj = conn.cursor()
        curObj.execute('SELECT actid, actname FROM public.activity;')
        rows = curObj.fetchall()
        curObj.close()
        return rows
    except psycopg2.DatabaseError as error:
        err = f"getListOfActivity error occured:{error}"
        print(err)
        print("Exception type:", type(error))
        return None


# *******************************************************************************
#       FEE MAINTENANCE FUNCTONS
#  We have a Payment table which contains clientid, amount paid, and paydate.
#   the identity column of the payment table is subsequent updated into
#     the "clients" table FeePaid column
#  NOTE that EVERY YEAR A NEW clientID, paydate will be added, so we ALWAYS
#  only retrieve payment for the current year.
#  FOR maintenance, maybe we can delete all payments of previous year.
# *******************************************************************************
# ================= add the fees paid update into payment table =================
# this function is called by addClient or Updateclient
# -------------------------------------------------------------------------------
def insupdPayment(cursor, clientID, amountPaid, familyID):

    dateEndOfYear = date(date.today().year, 12, 31)
    dt = datetime.now()
    dateUpdated = dt.replace(second=0, microsecond=0)

    try:
        if familyID != '0' and familyID != clientID:    # if client is not primary check whether family paid
            sqlFindFamilyPaid = f'''SELECT p."feeid"
                                   FROM public."family" f
                                   INNER JOIN public."payment" p ON p."clientid"=f."familyid"
                                              AND p."amount">60
                                              AND p."paydate"<'{dateEndOfYear}'
                                   WHERE f."clientid"={clientID} '''
            cursor.execute(sqlFindFamilyPaid)
            if cursor.rowcount > 0:    # if found family paid, return -1 * paymentid
                recPay = cursor.fetchone()
                feeid = recPay['feeid']
                return -1 * feeid
            else:
                return 0   # no one pays, return 0 so that it is not None
        elif amountPaid and amountPaid > 0:
            # --------- need to check if payment is done for this year ------
            findPaymentRecord = f'''SELECT feeid, clientid, amount, "paydate" FROM public.payment
                                    WHERE clientid={clientID} and "paydate"<'{dateEndOfYear}'; '''
            cursor.execute(findPaymentRecord)
            if cursor.rowcount > 0:
                recPay = cursor.fetchone()      # there should only only be one per year
                feeid = recPay['feeid']
                amount = recPay['amount']

                if amount != amountPaid:        # payment amount changed, we have to update it
                    updPayment = f'''UPDATE public.payment SET "amount"={amountPaid}, "paydate"='{dateUpdated}'
                                    WHERE "feeid"={feeid}; '''
                    cursor.execute(updPayment)
                return feeid                    # no matter what, we have to return the feeid
            else:                               # if there is no record of payment and amount is not 0
                insPay = f'''INSERT INTO public.payment("clientid", "amount", "paydate")
                            VALUES ( {clientID}, {amountPaid}, '{dateUpdated}' ) RETURNING feeid; '''
                cursor.execute(insPay)
                result = cursor.fetchone()
                feeid = result['feeid']
                return feeid        # ----- need to return back the fee id just inserted -----------
        else:
            return 0               # ---- no one paid, return 0 so that it is not None ------

    except psycopg2.DatabaseError as error:
        err = f"insupdPayment error occured:{error}"
        if conn:
            conn.rollback()
        print(err)
        print("Exception type:", type(error))
        raise (Exception(err))


# *******************************************************************************
#   CLIENT MAINTENANCE FUNCTIONS
# *******************************************************************************
# ============================= insAddFamilyGroup ===============================
def insAddFamilyGroup(familyID, clientID, firstName, lastName):

    curObj = conn.cursor()

    try:
        if familyID == '0':   # this is a primary family member adding for the first time, familyid=clientid
            sqlStmt = f'''INSERT INTO public."family" ( familyid, "name", clientid, "isPrimary" )
                    VALUES( {clientID}, '{firstName} {lastName}', {clientID}, '1' ); '''
            curObj.execute(sqlStmt)
            curObj.close()
            conn.commit()
            return clientID

        if familyID:    # if not None, we want to add this client to the prime member's family
            sqlTest = f'''SELECT familyID, clientID FROM public."family"
                        WHERE familyID={familyID} and clientid={clientID}; '''
            curObj.execute(sqlTest)
            if curObj.rowcount == 0:   # if not in table, insert as NON prime family member
                sqlStmt = f'''INSERT INTO public."family" ( familyid, "name", clientid, "isPrimary" )
                        VALUES( {familyID}, '{firstName} {lastName}', {clientID}, '0' ); '''
                curObj.execute(sqlStmt)
                curObj.close()
                conn.commit()
        #  ONLY if familyid is the primary client, update the firstName and last name so that it is sure correct
        if familyID == clientID:
            updFamilyName(clientID, firstName, lastName)

        return familyID

    except psycopg2.DatabaseError as error:
        err = f"insAddFamilyGroup error occured:{error}"
        if conn:
            conn.rollback()
        print(err)
        print("Exception type:", type(error))
        raise (Exception(err))


# ==================== find familyid based on primary member ====================
def findFamilyID(fullname):

    sqlSel = f'''SELECT familyid from public."family" WHERE "name"='{fullname}' AND "isPrimary"='1'; '''
    try:
        curObj = conn.cursor()
        curObj.execute(sqlSel)
        if curObj.rowcount > 0:
            results = curObj.fetchone()
            famID = results['familyid']
            return famID
        else:
            return None

    except psycopg2.DatabaseError as error:
        err = f"findFamilyID error occured:{error}"
        if conn:
            conn.rollback()
        print(err)
        print("Exception type:", type(error))
        raise (Exception(err))


# ==================== check and update name on familyID ========================
#  sometimes we messed up client on the name, when updating and the familyid
#   exists, we would update the full name as well
def updFamilyName(familyID, firstName, lastName):

    sqlSel = f'''Update public."family" SET "name"='{firstName} {lastName}' WHERE familyID ={familyID}; '''
    try:
        curObj = conn.cursor()
        curObj.execute(sqlSel)
        conn.commit()

    except psycopg2.DatabaseError as error:
        err = f"updFamilyName error occured:{error}"
        if conn:
            conn.rollback()
        print(err)
        print("Exception type:", type(error))
        raise (Exception(err))


# ===================== get a list of prime family member =======================
def getAllFamilyPrimeMember():
    sqlSel = '''SELECT familyid, "name" from public."family" WHERE "isPrimary"='1'; '''
    try:
        curObj = conn.cursor()
        curObj.execute(sqlSel)
        if curObj.rowcount > 0:
            results = curObj.fetchall()
            return results

    except psycopg2.DatabaseError as error:
        err = f"getAllFamilyPrimeMember error occured:{error}"
        if conn:
            conn.rollback()
        print(err)
        print("Exception type:", type(error))
        raise (Exception(err))


# =============================== addClient =====================================
def addClient(firstName,
              lastName,
              phoneNumber,
              address,
              ECName,
              ECPhone,
              Email,
              strPayment,
              familyID,
              MainActivity,
              dateRegistered,
              Remarks):

    dt = datetime.now()
    dateUpdated = dt.replace(second=0, microsecond=0)
    if strPayment:
        curPayment = int(strPayment)
    else:
        curPayment = 0

    # date of week  dt.strftime( '%A' )
    try:
        curObj = conn.cursor()
        sqlFindDuplicate = f'''SELECT id FROM public.clients where TRIM("phoneNumber")='{phoneNumber}' and
                             TRIM("firstName")='{firstName}' and TRIM("lastName")='{lastName}';  '''
        curObj.execute(sqlFindDuplicate)
        if curObj.rowcount == 0:    # insert only if not found
            insClient = f'''INSERT INTO public.clients( "firstName", "lastName", "phoneNumber", "address",
                            "ECName", "ECPhone", "Email", "MainActivity", "dateRegistered", "Remarks", "dateUpdated")
                            VALUES ( '{firstName}','{lastName}','{phoneNumber}', '{address}',
                                     '{ECName}', '{ECPhone}','{Email}', {MainActivity}, '{dateRegistered}',
                                     '{Remarks}', '{dateUpdated}') RETURNING id; '''
            curObj.execute(insClient)
            result = curObj.fetchone()
            insertedId = result['id']
            # ------- if familyid is provided, add into family table ----
            if familyID:    # if family id is provided
                insAddFamilyGroup(familyID, insertedId, firstName, lastName)

            paymentID = 0
            if curPayment >= 0:  # if registrant also paying now
                paymentID = insupdPayment(curObj, insertedId, curPayment, familyID)
            # elif curPayment < 0:  # if -1 then family paid
            #     paymentID = -1 * int( familyID )   # put in negative family ID as payment

            if paymentID != 0:
                sqlupdFeepaid = f'''UPDATE public.clients SET "FeePaid"={paymentID} WHERE "id"={insertedId}; '''
                curObj.execute(sqlupdFeepaid)

            curObj.close()
            conn.commit()
            return 0
        else:
            return -1

    except psycopg2.DatabaseError as error:
        err = f"addClient error occured:{error}"
        if conn:
            conn.rollback()
        print(err)
        print("Exception type:", type(error))
        raise (Exception(err))


# ============================= deleteClient ====================================
def deleteClient(id):
    sqlDel = f'''DELETE from public.clients WHERE "id"={id};
                 DELETE from public.qrcodes WHERE "clientid"={id};
                 DELETE from payment WHERE "clientid"={id};
              '''
    try:
        curObj = conn.cursor()
        curObj.execute(sqlDel)
        curObj.close()
        conn.commit()

    except psycopg2.DatabaseError as error:
        err = f"deleteClient error occured::{error}"
        if conn:
            conn.rollback()
        print(err)
        print("Exception type:", type(error))
        raise (Exception(err))

    # if all is well, remove the qrcode image if exists
    removeQRImg(id)
    return


# ============================= UpdateClient ====================================
def UpdateClient(id,
                 firstName,
                 lastName,
                 phoneNumber,
                 address,
                 ECName,
                 ECPhone,
                 Email,
                 strPayment,
                 familyID,
                 MajActivity,
                 dateRegistered,
                 Remarks):

    dt = datetime.now()
    dateUpdated = dt.replace(second=0, microsecond=0)
    if strPayment and strPayment.isdigit():
        curPayment = int(strPayment)
    else:
        curPayment = 0
    feeid = 0
    try:
        curObj = conn.cursor()
        # ------- if familyid is provided, add into family table ----
        if familyID:    # if family id is provided
            insAddFamilyGroup(familyID, id, firstName, lastName)

        if curPayment >= 0:      # if payment is still nothing don't bother
            feeid = insupdPayment(curObj, id, curPayment, familyID)
        # elif curPayment <=0 and familyID :    # must be family payment, -1
        #     feeid = -1 * int(familyID)

        # ---- if all goes well update the client
        updClient = f''' UPDATE public.clients
                    SET "firstName"='{firstName}', "lastName"='{lastName}', "phoneNumber"='{phoneNumber}',
                    address='{address}', "ECName"='{ECName}', "ECPhone"='{ECPhone}', "Email"='{Email}',
                    "FeePaid"={feeid}, "MainActivity"={MajActivity}, "dateRegistered"='{dateRegistered}',
                    "Remarks"='{Remarks}',"dateUpdated"='{dateUpdated}'
                    WHERE id={id};
                    '''
        curObj.execute(updClient)
        curObj.close()
        conn.commit()
        return 0
    except psycopg2.DatabaseError as error:
        err = f"UpdateClient error occured::{error}"
        if conn:
            conn.rollback()
        print(err)
        print("Exception type:", type(error))
        raise (Exception(err))


# ============================= Lookupclient =======================================
#  The queries below does look up of "family" database
def Lookupclient(firstName, lastName, phoneNumber):
    curObj = conn.cursor()
    sqlFindClient = ''
    if phoneNumber:         # if phone number is provided
        if not lastName:    # and no last name, use phone nunmber alone
            sqlFindClient = f'''SELECT DISTINCT f3.familyid,  a."id", a."firstName", a."lastName", a."phoneNumber",
                                a."ECName", a."ECPhone", a."dateRegistered",
                                CASE
                                    WHEN a."FeePaid"<0   THEN 'family'
                                    WHEN a."FeePaid">0   THEN d."amount" :: varchar(10)
                                END as "FeesPaid", b."actname" as "FavSport", c.qrimg
                                FROM public.clients a
                                LEFT JOIN public.activity b on a."MainActivity"=b.actID
                                LEFT JOIN public.payment d  on d."clientid"= a."id"
                                LEFT JOIN public.qrcodes c  on c."clientid"= a."id"
                                LEFT JOIN ( SELECT f1.familyid, f1.clientid
                                        FROM public."family" f
                                        LEFT JOIN public."family" f1 ON f1.familyID=f.familyID
                                        WHERE f.clientid IN ( SELECT "id" as "clientid" from public."clients"
                                        WHERE TRIM("phoneNumber") = '{phoneNumber}' ) ) f3 ON a."id"=f3.clientid
                                WHERE f3.familyid is not null
                                    OR ( TRIM(a."phoneNumber") = '{phoneNumber}' and f3.familyid is Null )
                                ORDER by f3.familyid, a."id"; '''
        else:   # otherwise use both last name and phone number
            sqlFindClient = f'''SELECT DISTINCT f3.familyid,  a."id", a."firstName", a."lastName", a."phoneNumber",
                                a."ECName", a."ECPhone", a."dateRegistered",
                                CASE
                                    WHEN a."FeePaid"<0   THEN 'family'
                                    WHEN a."FeePaid">0   THEN d."amount" :: varchar(10)
                                END as "FeesPaid", b."actname" as "FavSport", c.qrimg
                                FROM public.clients a
                                LEFT JOIN public.activity b on a."MainActivity"=b.actID
                                LEFT JOIN public.payment d  on d."clientid"= a."id"
                                LEFT JOIN public.qrcodes c  on c."clientid"= a."id"
                                LEFT JOIN ( SELECT f1.familyid, f1.clientid
                                        FROM public."family" f
                                        LEFT JOIN public."family" f1 ON f1.familyID=f.familyID
                                        WHERE f.clientid IN ( SELECT "id" as "clientid" from public."clients"
                                        WHERE TRIM("phoneNumber") = '{phoneNumber}' AND TRIM("lastName")='{lastName}' ) ) f3
                                              ON a."id"=f3.clientid
                                WHERE f3.familyid is not null
                                    OR ( TRIM(a."phoneNumber") = '{phoneNumber}' AND TRIM(a."lastName")='{lastName}' AND f3.familyid is Null )
                                ORDER by f3.familyid, a."id";  '''

    elif lastName:     # no phone number, then last name has to be filled
        if firstName:  # if first name is provided, include in search
            sqlFindClient = f'''SELECT DISTINCT f3.familyid,  a."id", a."firstName", a."lastName", a."phoneNumber",
                                a."ECName", a."ECPhone", a."dateRegistered",
                                CASE
                                    WHEN a."FeePaid"<0   THEN 'family'
                                    WHEN a."FeePaid">0   THEN d."amount" :: varchar(10)
                                END as "FeesPaid", b."actname" as "FavSport", c.qrimg
                                FROM public.clients a
                                LEFT JOIN public.activity b on a."MainActivity"=b.actID
                                LEFT JOIN public.payment d  on d."clientid"= a."id"
                                LEFT JOIN public.qrcodes c  on c."clientid"= a."id"
                                LEFT JOIN ( SELECT f1.familyid, f1.clientid
                                        FROM public."family" f
                                        LEFT JOIN public."family" f1 ON f1.familyID=f.familyID
                                        WHERE f.clientid IN ( SELECT "id" as "clientid" from public."clients"
                                        WHERE TRIM("lastName") = '{lastName}' AND TRIM("firstName")='{firstName}' ) ) f3
                                              ON a."id"=f3.clientid
                                WHERE f3.familyid is not null
                                    OR ( TRIM(a."lastName") = '{lastName}'  AND TRIM(a."firstName")='{firstName}' AND f3.familyid is Null )
                                ORDER by f3.familyid, a."id";   '''
        else:   # if we get here, we only have last name
            sqlFindClient = f'''SELECT DISTINCT f3.familyid,  a."id", a."firstName", a."lastName", a."phoneNumber",
                                a."ECName", a."ECPhone", a."dateRegistered",
                                CASE
                                    WHEN a."FeePaid"<0   THEN 'family'
                                    WHEN a."FeePaid">0   THEN d."amount" :: varchar(10)
                                END as "FeesPaid", b."actname" as "FavSport", c.qrimg
                                FROM public.clients a
                                LEFT JOIN public.activity b on a."MainActivity"=b.actID
                                LEFT JOIN public.payment d  on d."clientid"= a."id"
                                LEFT JOIN public.qrcodes c  on c."clientid"= a."id"
                                LEFT JOIN ( SELECT f1.familyid, f1.clientid
                                        FROM public."family" f
                                        LEFT JOIN public."family" f1 ON f1.familyID=f.familyID
                                        WHERE f.clientid IN ( SELECT "id" as "clientid" from public."clients"
                                        WHERE TRIM("lastName") = '{lastName}' ) ) f3 ON a."id"=f3.clientid
                                WHERE f3.familyid is not null
                                    OR ( TRIM(a."lastName") = '{lastName}' and f3.familyid is Null )
                                ORDER by f3.familyid, a."id"; '''
    elif firstName:
        sqlFindClient = f'''SELECT DISTINCT f3.familyid,  a."id", a."firstName", a."lastName", a."phoneNumber",
                            a."ECName", a."ECPhone", a."dateRegistered",
                            CASE
                                WHEN a."FeePaid"<0   THEN 'family'
                                WHEN a."FeePaid">0   THEN d."amount" :: varchar(10)
                            END as "FeesPaid", b."actname" as "FavSport", c.qrimg
                            FROM public.clients a
                            LEFT JOIN public.activity b on a."MainActivity"=b.actID
                            LEFT JOIN public.payment d  on d."clientid"= a."id"
                            LEFT JOIN public.qrcodes c  on c."clientid"= a."id"
                            LEFT JOIN ( SELECT f1.familyid, f1.clientid
                                        FROM public."family" f
                                        LEFT JOIN public."family" f1 ON f1.familyID=f.familyID
                                        WHERE f.clientid IN ( SELECT "id" as "clientid" from public."clients"
                                        WHERE TRIM("firstName") = '{firstName}' ) ) f3 ON a."id"=f3.clientid
                                WHERE f3.familyid is not null
                                    OR ( TRIM(a."firstName") = '{firstName}' and f3.familyid is Null )
                                ORDER by f3.familyid, a."id"; '''
    else:
        raise Exception("No Search parameter supplied")

    try:
        curObj.execute(sqlFindClient)
        rows = curObj.fetchall()
        curObj.close()
        return rows

    except psycopg2.DatabaseError as error:
        err = f"Lookupclient error occured:{error}"
        print(err)
        print("Exception type:", type(error))
        raise (Exception(err))


# ============================== get client attendance ==========================
# view attendance by clioent ID
def getClientAttendance(clientid):
    sqlAttendance = f"""
    SELECT a."clientid", c."firstName", c."lastName", s."date",
        CASE WHEN extract(isodow from s."date")=1 Then 'Monday'
            WHEN extract(isodow from s."date")=2 Then 'Tuesday'
            WHEN extract(isodow from s."date")=3 Then 'Wednesday'
            WHEN extract(isodow from s."date")=4 Then 'Thursday'
            WHEN extract(isodow from s."date")=5 Then 'Friday'
            WHEN extract(isodow from s."date")=6 Then 'Saturday'
            WHEN extract(isodow from s."date")=7 Then 'Sunday'
        END	as "dayOfWeek",
        CASE WHEN s."sessiontype"=0 Then 'morning'
            WHEN s."sessiontype"=1 Then 'afternoon'
            WHEN s."sessiontype"=2 Then 'evening'
        END as "session"
    FROM public."attendance" a
    inner join public."clients" c on a."clientid"=c."id"
    inner join public."sessions" s on s."sessionid"=a."sessionid"
    Where c."id"={clientid}
    order by s."date" DESC
    limit 10 """
    try:
        curObj = conn.cursor()
        curObj.execute(sqlAttendance)
        if curObj.rowcount <= 0:
            return None
        attendance = curObj.fetchall()
        curObj.close()
        return attendance

    except psycopg2.DatabaseError as error:
        err = f"getClientAttendance error occured:{error}"
        print(err)
        print("Exception type:", type(error))
        raise (Exception(err))


# =============================  getClientByID ==================================
def getClientByID(id):
    sqlSelect = f"""SELECT a.id, a."firstName", a."lastName", a."phoneNumber", a.address,
                   a."ECName", a."ECPhone", a."Email",
                   CASE
                       WHEN a."FeePaid"<0 THEN 'family'
                       WHEN a."FeePaid">0 THEN b."amount" :: varchar(10)
                   END as "FeesPaid", a."MainActivity", a."dateRegistered", a."Remarks",
                a."dateUpdated", f1.familyid as "FamilyID", f1."name" as "FamilyName"
                  FROM public.clients a
                  LEFT JOIN public.payment b on b."clientid"=a.id and b.feeid=a."FeePaid"
                  LEFT JOIN public.family  f ON f.clientid=a.id
                  LEFT JOIN public.family f1 ON f1.familyid=f.familyid AND f1."isPrimary"='1'
                  WHERE a."id"={id};"""
    try:
        curObj = conn.cursor()
        curObj.execute(sqlSelect)
        if curObj.rowcount <= 0:
            return None
        client = curObj.fetchone()
        curObj.close()
        return client

    except psycopg2.DatabaseError as error:
        err = f"getClientByID error occured:{error}"
        print(err)
        print("Exception type:", type(error))
        raise (Exception(err))


# ============================= func getAllFriends ==============================
def getAllFriends(getType):
    # ----------------------------------------------------------------------------------
    # |   return Clients.query.order_by( Clients.lastName, Clients.firstName),
    # |          note that paydate has to be less than end of this year, so that everyyear
    # |          a new paydate id enterend for the client
    # ----------------------------------------------------------------------------------
    dateEndOfYear = date(date.today().year, 12, 31)
    sqlStmt = ''
    try:
        curObj = conn.cursor()
        if getType == 2:    # ---- if query wants to include non-payee
            sqlStmt = f'''SELECT a."id", a."firstName", a."lastName", a."phoneNumber", a.address,
                        a."ECName", a."ECPhone", a."Email",
                        CASE
                            WHEN a."FeePaid"<0 THEN 'family'
                            WHEN a."FeePaid">0 THEN c."amount" :: varchar(10)
                        END as "FeesPaid", b."actname" as "FavSport", a."dateRegistered", a."dateUpdated"
                        FROM public.clients a
                        LEFT JOIN public.activity b on a."MainActivity"=b.actID
                        LEFT JOIN public.payment c on a."FeePaid" = c.feeid and c."paydate"<='{dateEndOfYear}'
                        ORDER by a."lastName", a."firstName";'''
        elif getType == 1:    # -- only unpaid registrants ------
            sqlStmt = f'''SELECT a."id", a."firstName", a."lastName", a."phoneNumber", a.address,
                        a."ECName", a."ECPhone", a."Email",
                        CASE
                            WHEN a."FeePaid"<0 THEN 'family'
                            WHEN a."FeePaid">0 THEN c."amount" :: varchar(10)
                        END as "FeesPaid", b."actname" as "FavSport", a."dateRegistered", a."dateUpdated"
                        FROM public.clients a
                        LEFT JOIN public.activity b on a."MainActivity"=b.actID
                        LEFT JOIN public.payment c on a."FeePaid" = c.feeid and c."paydate"<='{dateEndOfYear}'
                        WHERE a."FeePaid" is null OR a."FeePaid"=0
                        ORDER by a."lastName", a."firstName";'''
        elif getType == 0:    # --- only paid registrants -----
            sqlStmt = f'''SELECT a."id", a."firstName", a."lastName", a."phoneNumber", a.address,
                        a."ECName", a."ECPhone", a."Email",
                        CASE
                            WHEN a."FeePaid"<0 THEN 'family'
                            WHEN a."FeePaid">0 THEN c."amount" :: varchar(10)
                        END as "FeesPaid", b."actname" as "FavSport", a."dateRegistered", a."dateUpdated"
                        FROM public.clients a
                        LEFT JOIN public.activity b on a."MainActivity"=b.actID
                        LEFT JOIN public.payment c on a."FeePaid" = c.feeid and c."paydate"<='{dateEndOfYear}'
                        WHERE a."FeePaid" is not null AND a."FeePaid"!=0
                        ORDER by a."lastName", a."firstName";'''
        rows = None
        curObj.execute(sqlStmt)
        if curObj.rowcount > 1:
            rows = curObj.fetchall()
        elif curObj.rowcount == 1:
            rows = curObj.fetchone()
        curObj.close()
        return rows

    except Exception as error:
        err = f"getAllFriends error occured:{error}"
        print(err)
        print("Exception type:", type(error))
        raise (Exception(err))


# ************************************************************************************
#       ATTENDANCE FUNCTIONS
#   we have sessions table which contains sessionID, date, and sessionType(0=morning,
#   1=afternoon, 2=evening)
#   Then attendance table contains simply sessionID and clientIDs, easily getting
#  all attendees for a particular session.
# ************************************************************************************
# ======================= getCurrentSessionID() ======================================
def getCurrentSessionID(day, sessionType):
    if day is None or sessionType is None:
        return 0
    # ------- get today's datetime and decide whether it is morning, afternoon, evening
    curObj = conn.cursor()
    try:
        sqlSel = f'''Select "sessionid" from public.sessions where "date"='{day}' and "sessiontype"={sessionType};'''
        ret = curObj.execute(sqlSel)
        if curObj.rowcount > 0:
            ret = curObj.fetchone()
            curObj.close()
            return ret['sessionid']
        else:
            sqlIns = f'''INSERT INTO public.sessions("date", "sessiontype") VALUES( '{day}', {sessionType}) RETURNING sessionid'''
            curObj.execute(sqlIns)
            ret = curObj.fetchone()
            curObj.close()
            conn.commit()

            return ret['sessionid']

    except psycopg2.DatabaseError as error:
        conn.rollback()
        err = f"Select sessions table error occured:{error}"
        print(err)
        print("Exception type:", type(error))
        raise (Exception(err))


# ======================= add current attendee into attendance table =================
def addAttendee(clientID, sessionID):
    # ------- clientData should come in as a space separated list --------
    # --------   format( DMBC4R ID Peter Chan 416-111-2222) --------------
    # first check if client already checked in, in case QRCode scanned twice

    findRec = f'''SELECT "clientid" from public.attendance
                  WHERE "sessionid"='{sessionID}' AND "clientid"={clientID} ;'''
    try:
        curObj = conn.cursor()
        curObj.execute(findRec)
        if curObj.rowcount > 0:
            curObj.close()
            return 0    # found it there already, nothing to do
        else:
            sqlAdd = f'''INSERT INTO public.attendance( "sessionid", "clientid") VALUES( {sessionID}, {clientID}); '''
            curObj.execute(sqlAdd)
            curObj.close()
            conn.commit()
            return 0
    except psycopg2.DatabaseError as error:
        err = f"Select/insert attendance table error occured:{error}"
        print(err)
        print("Exception type:", type(error))
        raise (Exception(err))


# ======================= delete current attendee into attendance table =================
def removeAttendee(clientID, sessionID):
    delAttendee = f'''DELETE from public.attendance
                      WHERE "sessionid"='{sessionID}' AND "clientid"={clientID} ;'''
    try:
        curObj = conn.cursor()
        curObj.execute(delAttendee)
        curObj.close()
        conn.commit()
        return 0
    except psycopg2.DatabaseError as error:
        err = f"Delete attendee from  attendance table error occured:{error}"
        print(err)
        print("Exception type:", type(error))
        raise (Exception(err))


# ============================= func getAllCurAttendees ==============================
def getAllCurAttendees(sessionID):
    if sessionID is None:
        return
    # ------- the display orders by the sequence of entry to reflect the true scenario ---------
    # ------- if necessary, later add order by a."lastName", a."firstName
    sqlGetAllAttendees = f'''SELECT a.id, a."firstName", a."lastName", a."phoneNumber", a."ECName", a."ECPhone",
                                CASE
                                    WHEN a."FeePaid"<0   THEN 'family'
                                    WHEN a."FeePaid">0   THEN d."amount" :: varchar(10)
                                END as "FeesPaid"
                            FROM public.attendance b
                            INNER JOIN public."clients" a ON a."id"=b."clientid"
                            LEFT JOIN public.payment d  on d."clientid"= a."id"
                            WHERE b."sessionid"={sessionID}
                            ORDER by b.seqid '''

    try:
        curObj = conn.cursor()
        curObj.execute(sqlGetAllAttendees)
        if curObj.rowcount > 0:
            rows = curObj.fetchall()
        else:
            rows = None
        curObj.close()      # -- release the memory?
        return rows

    except psycopg2.DatabaseError as error:
        err = f"getAllCurrentAttendees error occured:{error}"
        print(err)
        print("Exception type:", type(error))
        raise (Exception(err))


# *************************************************************************************
#   QR CODE functions
# *************************************************************************************
# ============================= func insupdQRCode =====================================
def insupdQRCode(id, firstName, lastName, phoneNum):

    isIns = True
    try:
        # ---- check if image exists --------------
        sqlGetImg = f"""Select "clientid" from public.qrcodes where "clientid"={id};"""
        curObj = conn.cursor()
        curObj.execute(sqlGetImg)
        if curObj.rowcount >= 1:     # there is already a row, must be update
            isIns = False
        curObj.close()

    except psycopg2.DatabaseError as error:
        err = f"Select qrcode error occured:{error}"
        print(err)
        print("Exception type:", type(error))
        raise (Exception(err))

    # formulate the string to code as QR img
    pathToImg = genQRCode(id, firstName, lastName, phoneNum)
    if not pathToImg:   # if for some reason fails
        raise Exception(f"cannot create qrcode for {id}, {firstName}, {lastName}, {phoneNum}")

    sqlstr = ""
    if isIns:
        sqlstr = f"""INSERT INTO public.qrcodes( clientid, "firstName", "lastName", "phoneNum", "qrimg")
                     VALUES ({id}, '{firstName}', '{lastName}', '{phoneNum}', '{pathToImg}' );"""
    else:
        sqlstr = f"""UPDATE public.qrcodes set "qrimg"='{pathToImg}' WHERE "clientid"={id}"""
    try:
        curObj = conn.cursor()
        curObj.execute(sqlstr)
        conn.commit()
        curObj.close()

    except psycopg2.DatabaseError as error:
        err = f"Inserting qrcode error occured:{error}"
        if conn:
            conn.rollback()
        print(err)
        print("Exception type:", type(error))
        raise (Exception(err))


# ============================= func updateAllQrcodes =================================
# ----- function to either insert or update all images.  This will not be done often
def updateAllQrcodes():
    # -------- get record set of id, firstName, lastName, phoneNumber from client table ----
    try:
        curObj = conn.cursor()
        sqlStmt = '''SELECT "id", "firstName", "lastName", "phoneNumber", "FeePaid"
                     FROM public.clients
                     WHERE "FeePaid" is not NULL AND "FeePaid"!=0
                     order by "lastName", "firstName" '''

        rows = None
        curObj.execute(sqlStmt)
        if curObj.rowcount > 1:
            rows = curObj.fetchall()
        elif curObj.rowcount == 1:
            rows = curObj.fetchone()
        curObj.close()
        for row in rows:
            insupdQRCode(row["id"], row["firstName"], row["lastName"], row["phoneNumber"])

    except psycopg2.DatabaseError as error:
        err = f"Select id error occured:{error}"
        print(err)
        print("Exception type:", type(error))
        raise (Exception(err))


def checkPass(userID, password):
    try:
        curObj = conn.cursor()
        sql = f"""Select ("passHash" = crypt('{password}', "passHash" ) ) as passmatched
                From public."user_account" Where "userID"='{userID}' """
        curObj.execute(sql)
        match = curObj.fetchone()
        curObj.close()
        return match

    except psycopg2.DatabaseError as error:
        err = f"checkPass error occured:{error}"
        print(err)
        print("Exception type:", type(error))
        raise (Exception(err))
