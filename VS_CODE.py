from flask import Flask, request, jsonify
import pandas as pd
import tensorflow as tf
import joblib
import os

app = Flask(__name__)

# ----------------------------
# Load Model and Scalers
# ----------------------------
MODEL_PATH = "solar_model.keras"
SCALER_X_PATH = "scaler_X.save"
SCALER_Y_PATH = "scaler_Y.save"

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError("Model file not found.")

if not os.path.exists(SCALER_X_PATH) or not os.path.exists(SCALER_Y_PATH):
    raise FileNotFoundError("Scaler file(s) not found.")

model = tf.keras.models.load_model(MODEL_PATH)
scaler_X = joblib.load(SCALER_X_PATH)
scaler_Y = joblib.load(SCALER_Y_PATH)

INPUT_COLS = ["TEMP", "IRR", "DC_Current"]

# ----------------------------
# Prediction Route
# ----------------------------
@app.route("/predict", methods=["POST"])
def predict():
    try:
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        data = request.get_json()

        for col in INPUT_COLS:
            if col not in data:
                return jsonify({"error": f"Missing field: {col}"}), 400

        try:
            values = [float(data[col]) for col in INPUT_COLS]
        except ValueError:
            return jsonify({"error": "All inputs must be numeric"}), 400

        # --------- ML PREDICTION ----------
        input_df = pd.DataFrame([values], columns=INPUT_COLS)
        input_scaled = scaler_X.transform(input_df)

        pred_scaled = model.predict(input_scaled, verbose=0)
        pred = scaler_Y.inverse_transform(pred_scaled)

        # --------- STEP 1: NORMALIZE OUTPUT ----------
        NORMALIZATION_FACTOR = 7000.0

        base_low = float(pred[0][0]) / NORMALIZATION_FACTOR
        base_mid = float(pred[0][1]) / NORMALIZATION_FACTOR
        base_high = float(pred[0][2]) / NORMALIZATION_FACTOR

        # --------- STEP 2: SENSOR INFLUENCE ----------
        irr = float(data["IRR"])
        current = float(data["DC_Current"])

        irr_norm = irr / 4095.0          # 0 → 1
        current_norm = current / 4.0     # assume max ~4A

        # --------- STEP 3: FINAL POWER ----------
        factor = (0.5 + 2.5 * irr_norm) * (0.5 + 2.0 * current_norm)

        power_low = base_low * factor * 10
        power_mid = base_mid * factor * 10
        power_high = base_high * factor * 10

        return jsonify({
            "POWER_LOW": round(power_low, 2),
            "POWER_MID": round(power_mid, 2),
            "POWER_HIGH": round(power_high, 2),
            "UNIT": "W"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ----------------------------
# Health Check
# ----------------------------
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "Solar Prediction API Running"})


# ----------------------------
# Run Server
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)