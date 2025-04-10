from flask import Flask, render_template, request, redirect, url_for, jsonify
import mysql.connector
from datetime import date
import base64
import urllib.parse

app = Flask(__name__)

# MySQL 연결 설정
db_config = {
    'host': 'chambit.mysql.pythonanywhere-services.com',
    'user': 'chambit',
    'password': 'chab!!23',
    'database': 'chambit$concert_application'
}

# 데이터베이스 테이블 생성
def init_db():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS `202506` (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            contact VARCHAR(255) NOT NULL,
            last_booked_date DATE NOT NULL,
            seat1 VARCHAR(255) DEFAULT "",
            seat2 VARCHAR(255) DEFAULT "",
            seat3 VARCHAR(255) DEFAULT "",
            seat4 VARCHAR(255) DEFAULT "",
            attend BOOLEAN DEFAULT FALSE,
            UNIQUE KEY `unique_name_contact` (name, contact)
        )
    ''')
    conn.commit()
    conn.close()

# DB 초기화
init_db()

# 데이터 인코딩 (Base64 사용)
def encode_data(data):
    # 데이터 길이를 늘리기 위해 접두어 추가
    prefixed_data = f"RESERVATION_ID:{data}"
    return base64.urlsafe_b64encode(prefixed_data.encode()).decode()

# 데이터 디코딩 (Base64 사용)
def decode_data(encoded_data):
    decoded = base64.urlsafe_b64decode(encoded_data.encode()).decode()
    # 접두어 제거
    if decoded.startswith("RESERVATION_ID:"):
        return decoded[len("RESERVATION_ID:"):]
    return decoded

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form.get("name")
        contact = request.form.get("contact").replace("-", "")
        attendees = request.form.get("attendees")
        selected_seats = request.form.get("selected_seats").split(",") if request.form.get("selected_seats") else []

        if name and contact and attendees:
            seat1 = selected_seats[0] if len(selected_seats) > 0 else ""
            seat2 = selected_seats[1] if len(selected_seats) > 1 else ""
            seat3 = selected_seats[2] if len(selected_seats) > 2 else ""
            seat4 = selected_seats[3] if len(selected_seats) > 3 else ""

            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO `202506` (name, contact, last_booked_date, seat1, seat2, seat3, seat4, attend)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                last_booked_date=%s, seat1=%s, seat2=%s, seat3=%s, seat4=%s, attend=%s
            """, (name, contact, date.today(), seat1, seat2, seat3, seat4, False,
                  date.today(), seat1, seat2, seat3, seat4, False))
            conn.commit()

            # 예약 ID 가져오기
            cursor.execute("SELECT id FROM `202506` WHERE name = %s AND contact = %s", (name, contact))
            reservation_id = cursor.fetchone()[0]
            conn.close()

            # QR 코드 데이터 (예약 ID만 포함)
            qr_data = str(reservation_id)
            encoded_data = encode_data(qr_data)
            encoded_url_data = urllib.parse.quote(encoded_data)
            qr_link = url_for('show_qrcode', encoded_data=encoded_url_data, _external=True)

            return jsonify({"success": True, "qr_data": encoded_data, "qr_link": qr_link})

    return render_template("index.html")

@app.route("/check_existing", methods=["POST"])
def check_existing():
    name = request.form.get("name")
    contact = request.form.get("contact").replace("-", "")
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT seat1, seat2, seat3, seat4 FROM `202506`
        WHERE name=%s AND contact=%s
    """, (name, contact))
    result = cursor.fetchone()
    conn.close()

    if result:
        seats = [seat for seat in result if seat]
        return jsonify({"seats": seats})
    return jsonify({"seats": []})

@app.route("/all_seats", methods=["GET"])
def all_seats():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT seat1, seat2, seat3, seat4 FROM `202506`")
    results = cursor.fetchall()
    conn.close()

    all_seats = []
    for row in results:
        all_seats.extend([seat for seat in row if seat])
    return jsonify({"seats": all_seats})

@app.route("/cancel_reservation", methods=["POST"])
def cancel_reservation():
    name = request.form.get("name")
    contact = request.form.get("contact").replace("-", "")
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM `202506` WHERE name = %s AND contact = %s", (name, contact))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/delete_application", methods=["POST"])
def delete_application():
    id = request.form.get("id")
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM `202506` WHERE id = %s", (id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/clear_attendance", methods=["POST"])
def clear_attendance():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("UPDATE `202506` SET attend = FALSE")
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/list")
def list_applications():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, contact, last_booked_date, seat1, seat2, seat3, seat4, attend FROM `202506`")
    applications = cursor.fetchall()
    conn.close()

    return render_template("list.html", applications=applications)

@app.route('/qrscan', methods=['GET', 'POST'])
def qrscan():
    if request.method == 'POST':
        encoded_data = request.form.get('encoded_data')
        if not encoded_data:
            return jsonify({"success": False, "message": "QR 코드 데이터가 없습니다."})

        print("Received encoded_data:", encoded_data)

        try:
            reservation_id = decode_data(encoded_data)
            print("Decoded reservation_id:", reservation_id)
        except Exception as e:
            print("Decoding error:", str(e))
            return jsonify({"success": False, "message": "QR 코드 디코딩 실패: " + str(e)})

        try:
            reservation_id = int(reservation_id)
        except ValueError:
            print("Invalid reservation_id format:", reservation_id)
            return jsonify({"success": False, "message": "유효하지 않은 예약 ID 형식입니다."})

        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT name, seat1, seat2, seat3, seat4 FROM `202506` WHERE id = %s", (reservation_id,))
            row = cursor.fetchone()
            seats = []
            if row:
                name = row[0]
                for seat in row[1:]:
                    if seat:
                        seats.append(seat)
                # 참석 여부를 TRUE로 업데이트
                cursor.execute("UPDATE `202506` SET attend = TRUE WHERE id = %s", (reservation_id,))
                conn.commit()
                conn.close()
                print("Found reservation for ID:", reservation_id, "Name:", name, "Seats:", seats)
                return jsonify({
                    "success": True,
                    "name": name,
                    "seats": seats,
                    "message": [
                        f"{name}님 환영합니다.",
                        f"예약하신 좌석은 {', '.join(seats)} 입니다.",
                        "즐거운 관람 되시길 바랍니다."
                    ]
                })
            else:
                conn.close()
                print("No reservation found for ID:", reservation_id)
                return jsonify({
                    "success": False,
                    "message": ["예약 정보를 찾을 수 없습니다."]
                })
        except mysql.connector.Error as db_error:
            print("Database error:", str(db_error))
            return jsonify({"success": False, "message": ["데이터베이스 오류: " + str(db_error)]})
        except Exception as e:
            print("Unexpected error:", str(e))
            return jsonify({"success": False, "message": ["서버 오류: " + str(e)]})
    return render_template('qrscan.html')

@app.route('/qrcode/<encoded_data>')
def show_qrcode(encoded_data):
    encoded_data = urllib.parse.unquote(encoded_data)
    return render_template('qrcode.html', encoded_data=encoded_data)

if __name__ == "__main__":
    app.run(debug=True)
