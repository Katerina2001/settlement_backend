from flask import Blueprint, request, jsonify
import datetime
import pymysql

toll_bp = Blueprint("toll_bp", __name__)

# Διαδρομή για διελεύσεις ανά σταθμό
@toll_bp.route("/tollStationPasses/<tollStationID>/<date_from>/<date_to>", methods=["GET"])
def get_toll_station_passes(tollStationID, date_from, date_to):
    try:
        # Μετατροπή των ημερομηνιών στη σωστή μορφή
        date_from_formatted = datetime.datetime.strptime(date_from, "%Y%m%d").strftime("%Y-%m-%d")
        date_to_formatted = datetime.datetime.strptime(date_to, "%Y%m%d").strftime("%Y-%m-%d")

        # Τρέχον timestamp
        request_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        # Σύνδεση με τη βάση δεδομένων
        conn = pymysql.connect(host="localhost", user="root", password="", database="settlement")
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # Λήψη πληροφοριών για τον σταθμό
        cursor.execute("SELECT tollID, operator FROM TollStation WHERE tollID = %s", (tollStationID,))
        station = cursor.fetchone()

        if not station:
            return jsonify({"status": "failed", "info": "Toll station not found"}), 400

        stationOperator = station["operator"]

        # Λήψη διελεύσεων
        query = """
            SELECT p.passageID, p.timestamp, p.tagRef AS tagID, t.providerID AS tagProvider, p.charge AS passCharge
            FROM Passage p
            JOIN Tag t ON p.tagRef = t.tagID
            WHERE p.tollID = %s 
            AND p.timestamp BETWEEN %s AND %s
            ORDER BY p.timestamp ASC
        """
        cursor.execute(query, (tollStationID, date_from_formatted, date_to_formatted))
        passes = cursor.fetchall()

        # Αν δεν υπάρχουν δεδομένα, επιστρέφουμε 204 No Content
        if not passes:
            return jsonify({"status": "No Content"}), 204

        # Διαμόρφωση της λίστας διελεύσεων
        pass_list = []
        for idx, passage in enumerate(passes, start=1):
            pass_list.append({
                "passIndex": idx,
                "passID": passage["passageID"],
                "timestamp": passage["timestamp"],  # Είναι ήδη σε μορφή "YYYY-MM-DD hh:mm"
                "tagID": passage["tagID"],
                "tagProvider": passage["tagProvider"],
                "passType": "home" if passage["tagProvider"] == stationOperator else "visitor",
                "passCharge": passage["passCharge"]
            })

        # Δημιουργία του τελικού JSON response
        response = {
            "stationID": tollStationID,
            "stationOperator": stationOperator,
            "requestTimestamp": request_timestamp,
            "periodFrom": date_from,
            "periodTo": date_to,
            "nPasses": len(pass_list),
            "passList": pass_list
        }

        return jsonify(response), 200

    except Exception as e:
        return jsonify({"status": "failed", "info": str(e)}), 500

    finally:
        cursor.close()
        conn.close()
