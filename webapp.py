from flask import Flask, request, Response, render_template_string
import threading
import queue
import json
import datetime  # import datetime for timestamps

from main import schedule_month_shifts, get_provider

app = Flask(__name__)
# Global variable to manage cancellation
scheduler_stop_event = None

FORM_HTML = """
<!doctype html>
<html>
  <head>
    <title>Schedule Shifts</title>
    <style>
      body {
        font-family: Arial, sans-serif;
        background: #f2f2f2;
        margin: 0;
        padding: 20px;
      }
      h2, h3 { color: #333; }
      .container {
        display: flex;
        gap: 20px;
      }
      .column {
        flex: 1;
        background: #fff;
        padding: 20px;
        box-sizing: border-box;
        border-radius: 5px;
        box-shadow: 0 0 10px rgba(0,0,0,0.1);
      }
      input[type="text"], input[type="number"], input[type="month"], input[type="date"], textarea, select {
        width: 100%;
        max-width: 100%;
        box-sizing: border-box;
        padding: 10px;
        margin: 5px 0 15px 0;
        border: 1px solid #ccc;
        border-radius: 4px;
      }
      input[type="submit"], button {
        background-color: #4CAF50;
        color: white;
        padding: 10px 15px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
      }
      input[type="submit"]:hover, button:hover {
        background-color: #45a049;
      }
      #stopButton {
        background-color: red;
      }
      #logs {
        background: #000;
        color: #0f0;
        padding: 10px;
        height: 300px;
        overflow-y: scroll;
        border-radius: 4px;
        white-space: pre-wrap;
      }
      .auth-field {
        display: none;
      }
      .auth-field.active {
        display: block;
      }
      .provider-selector {
        background: #f8f9fa;
        border: 2px solid #e9ecef;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 20px;
      }
      .provider-selector label {
        font-weight: bold;
        color: #495057;
        margin-bottom: 8px;
        display: block;
      }
      .provider-selector select {
        width: 100%;
        padding: 12px;
        font-size: 16px;
        border: 2px solid #ced4da;
        border-radius: 6px;
        background-color: white;
        margin: 0;
      }
      .provider-selector select:focus {
        outline: none;
        border-color: #4CAF50;
        box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);
      }
      .date-picker {
        background: #f8f9fa;
        border: 2px solid #e9ecef;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 20px;
      }
      .date-picker label {
        font-weight: bold;
        color: #495057;
        margin-bottom: 8px;
        display: block;
      }
      .date-picker input[type="month"] {
        width: 100%;
        padding: 12px;
        font-size: 16px;
        border: 2px solid #ced4da;
        border-radius: 6px;
        background-color: white;
        margin: 0;
      }
      .date-picker input[type="month"]:focus {
        outline: none;
        border-color: #4CAF50;
        box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);
      }
    </style>
  </head>
  <body>
    <h2>Autofill Time Tracking Shifts</h2>
    <p>This tool schedules shifts for the selected month. Choose your provider (Factorial or Endalia), paste the corresponding CURL command, and select the month you want to apply.</p>
    <p>There is a button to stop the process if needed.</p>
    <div class="container">
      <div class="column">
        <div class="provider-selector">
          <label for="provider">Choose Time Tracking Provider:</label>
          <select name="provider" id="provider">
            <option value="endalia">Endalia</option>
            <option value="factorial">Factorial</option>
          </select>
        </div>
        <form id="scheduleForm">
          Employee ID: <input type="text" name="employee_id" id="employee_id"><br>
          <div id="cookieField" class="auth-field">
            Cookie: <input type="text" name="cookie" id="cookie"><br>
          </div>
          <div id="authTokenField" class="auth-field active">
            Auth Token: <input type="text" name="auth_token" id="auth_token"><br>
          </div>
          <div class="date-picker">
            <label for="monthYear">Select Month and Year:</label>
            <input type="month" name="monthYear" id="monthYear" value="2025-05">
            <!-- Safari fallback -->
            <div id="safariDateFallback" style="display: none;">
              <select id="safariMonth" style="width: 48%; display: inline-block; margin-right: 4%;">
                <option value="01">January</option>
                <option value="02">February</option>
                <option value="03">March</option>
                <option value="04">April</option>
                <option value="05" selected>May</option>
                <option value="06">June</option>
                <option value="07">July</option>
                <option value="08">August</option>
                <option value="09">September</option>
                <option value="10">October</option>
                <option value="11">November</option>
                <option value="12">December</option>
              </select>
              <select id="safariYear" style="width: 48%; display: inline-block;">
                <option value="2024">2024</option>
                <option value="2025" selected>2025</option>
                <option value="2026">2026</option>
              </select>
            </div>
          </div>
          <input type="submit" value="Schedule Shifts">
        </form>
        <!-- Stop form hidden by default and separated by margin -->
        <form id="stopForm" style="margin-top: 20px; display: none;">
          <input type="submit" id="stopButton" value="Stop Process">
        </form>
      </div>
      <div class="column">
        <h3>Paste Curl Text:</h3>
        <textarea id="curlInput" rows="15" placeholder="Paste your curl command here..."></textarea>
        <button id="parseCurl">Parse Curl</button>
      </div>
    </div>
    <h3>Logs:</h3>
    <div id="logs"></div>
    <script>
      const scheduleForm = document.getElementById("scheduleForm");
      const stopForm = document.getElementById("stopForm");
      const logsDiv = document.getElementById("logs");
      const parseCurlBtn = document.getElementById("parseCurl");
      const curlInput = document.getElementById("curlInput");
      const providerSelect = document.getElementById("provider");
      const cookieField = document.getElementById("cookieField");
      const authTokenField = document.getElementById("authTokenField");
      const monthYearInput = document.getElementById("monthYear");
      const safariDateFallback = document.getElementById("safariDateFallback");
      const safariMonth = document.getElementById("safariMonth");
      const safariYear = document.getElementById("safariYear");

      // Detect Safari and show fallback if needed
      const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
      if (isSafari) {
        // Test if month input is supported
        const testInput = document.createElement('input');
        testInput.type = 'month';
        if (testInput.type !== 'month') {
          // Month input not supported, show fallback
          monthYearInput.style.display = 'none';
          safariDateFallback.style.display = 'block';
        }
      }

      // Sync Safari fallback with main input
      function updateFromSafariFallback() {
        const month = safariMonth.value;
        const year = safariYear.value;
        monthYearInput.value = `${year}-${month}`;
      }

      safariMonth.addEventListener('change', updateFromSafariFallback);
      safariYear.addEventListener('change', updateFromSafariFallback);

      // Toggle auth fields based on provider selection
      providerSelect.addEventListener("change", function() {
        const provider = this.value;
        if (provider === "factorial") {
          cookieField.classList.add("active");
          authTokenField.classList.remove("active");
        } else if (provider === "endalia") {
          cookieField.classList.remove("active");
          authTokenField.classList.add("active");
        }
      });

      // Parse curl to extract authentication and employeeId based on provider
      parseCurlBtn.addEventListener("click", function() {
        const curlText = curlInput.value;
        const provider = providerSelect.value;
        
        if (provider === "factorial") {
          // Regex to extract Cookie header value for Factorial
          const cookieMatch = curlText.match(/-H\\s+['"]Cookie:\\s*([^'"]+)['"]/);
          if (cookieMatch && cookieMatch[1]) {
            document.getElementById("cookie").value = cookieMatch[1].trim();
          }
          // Regex to extract employeeId in JSON payload (--data-binary)
          const employeeIdMatch = curlText.match(/"employeeId"\\s*:\\s*(\\d+)/);
          if (employeeIdMatch && employeeIdMatch[1]) {
            document.getElementById("employee_id").value = employeeIdMatch[1].trim();
          }
        } else if (provider === "endalia") {
          // Regex to extract Authorization Bearer token for Endalia
          const authMatch = curlText.match(/-H\\s+['"]Authorization:\\s*Bearer\\s+([^'"]+)['"]/);
          if (authMatch && authMatch[1]) {
            document.getElementById("auth_token").value = authMatch[1].trim();
          }
          // For Endalia, employee ID might be in the JWT token payload or in the JSON data
          // First try to extract from JSON data if present
          const empIdMatch = curlText.match(/"EmpID"\\s*:\\s*"?(\\d+)"?/);
          if (empIdMatch && empIdMatch[1]) {
            document.getElementById("employee_id").value = empIdMatch[1].trim();
          } else {
            // Try to decode JWT to get employee ID (basic extraction)
            if (authMatch && authMatch[1]) {
              try {
                const tokenParts = authMatch[1].split('.');
                if (tokenParts.length >= 2) {
                  const payload = JSON.parse(atob(tokenParts[1]));
                  if (payload.empid) {
                    document.getElementById("employee_id").value = payload.empid;
                  }
                }
              } catch (e) {
                console.log("Could not decode JWT token for employee ID");
              }
            }
          }
        }
      });

      scheduleForm.addEventListener("submit", function(e) {
        e.preventDefault();
        // Validation: ensure all required fields are filled
        const employeeId = document.getElementById("employee_id").value.trim();
        const provider = document.getElementById("provider").value; // Get from external selector
        const monthYear = document.getElementById("monthYear").value.trim();
        
        if (!monthYear) {
          alert("Please select a month and year.");
          return;
        }
        
        // Parse year and month from the month input (format: YYYY-MM)
        const [year, month] = monthYear.split('-');
        
        let authValid = false;
        if (provider === "factorial") {
          const cookie = document.getElementById("cookie").value.trim();
          authValid = !!cookie;
        } else if (provider === "endalia") {
          const authToken = document.getElementById("auth_token").value.trim();
          authValid = !!authToken;
        }
        
        if (!employeeId || !authValid || !year || !month) {
          alert("Please fill in all required fields before scheduling.");
          return;
        }
        
        logsDiv.innerText = "";
        // Reveal stop button once scheduling starts
        stopForm.style.display = "block";
        
        // Create form data and add provider, year, and month values manually
        const formData = new FormData(scheduleForm);
        formData.append("provider", provider);
        formData.append("year", year);
        formData.append("month", month);
        
        fetch("/schedule", { method: "POST", body: formData })
          .then(response => {
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            function read() {
              reader.read().then(({ done, value }) => {
                if (done) return;
                logsDiv.innerText += decoder.decode(value);
                logsDiv.scrollTop = logsDiv.scrollHeight;
                read();
              });
            }
            read();
          });
      });

      stopForm.addEventListener("submit", function(e) {
        e.preventDefault();
        fetch("/stop", { method: "POST" })
          .then(response => response.text())
          .then(text => {
            logsDiv.innerText += "\\n" + text;
            logsDiv.scrollTop = logsDiv.scrollHeight;
          });
      });
    </script>
  </body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(FORM_HTML)

@app.route("/schedule", methods=["POST"])
def schedule():
    global scheduler_stop_event
    
    # Get form data
    employee_id = int(request.form["employee_id"])
    provider_type = request.form["provider"]
    year = int(request.form["year"])
    month = int(request.form["month"])
    
    # Get authentication data based on provider type
    if provider_type == "factorial":
        auth_data = request.form.get("cookie", "")
    elif provider_type == "endalia":
        auth_data = request.form.get("auth_token", "")
    else:
        return Response("Invalid provider type", status=400)
    
    if not auth_data:
        return Response("Authentication data is required", status=400)
    
    # Create configuration for the provider
    config = {
        "employee_id": employee_id,
        "provider": provider_type
    }
    
    if provider_type == "factorial":
        config["cookie"] = auth_data
    elif provider_type == "endalia":
        config["auth_token"] = auth_data
    
    q = queue.Queue()
    scheduler_stop_event = threading.Event()

    # Updated logger now adds a timestamp to every log line
    def logger(msg):
        timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        q.put(f"{timestamp} {msg}\n")

    def run_scheduler():
        try:
            # Get the appropriate provider
            provider, auth_data_processed = get_provider(provider_type, config)
            
            # Run the scheduler
            result = schedule_month_shifts(provider, employee_id, year, month, auth_data_processed, logger=logger, stop_event=scheduler_stop_event)
            q.put("FINAL_RESULT:" + json.dumps(result, indent=2))
        except Exception as e:
            logger(f"Error: {str(e)}")
            q.put("FINAL_RESULT:" + json.dumps({"error": str(e)}, indent=2))
        finally:
            q.put(None)  # use sentinel to signal end

    threading.Thread(target=run_scheduler).start()

    def stream():
        while True:
            line = q.get()
            if line is None:
                break
            # Check for the final JSON result marker and add a separator if needed.
            if line.startswith("FINAL_RESULT:"):
                yield "\n" + "="*50 + "\nFinal Result:\n" + line.replace("FINAL_RESULT:", "") + "\n" + "="*50 + "\n"
            else:
                yield line

    return Response(stream(), mimetype="text/plain")

@app.route("/stop", methods=["POST"])
def stop():
    global scheduler_stop_event
    if scheduler_stop_event:
        scheduler_stop_event.set()
        return "Process cancellation requested."
    return "No process running."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True, threaded=True)
