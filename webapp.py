from flask import Flask, request, Response, render_template_string
import threading
import queue
import json
import datetime  # import datetime for timestamps

from main import schedule_month_shifts

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
      input[type="text"], input[type="number"], textarea {
        width: 95%;
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
    </style>
  </head>
  <body>
    <h2>Autofill Factorial Shifts</h2>
    <p>This tool generates three shifts per day. You need to paste a valid GraphQL CURL command in the provided textarea and finally select the month you want to apply.</p>
    <p>There is a button to stop the process if needed.</p>
    <div class="container">
      <div class="column">
        <form id="scheduleForm">
          Employee ID: <input type="text" name="employee_id" id="employee_id"><br>
          Cookie: <input type="text" name="cookie" id="cookie"><br>
          Year: <input type="number" name="year" value="2025"><br>
          Month: <input type="number" name="month" value="2"><br>
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

      // Parse curl to extract cookie and employeeId
      parseCurlBtn.addEventListener("click", function() {
        const curlText = curlInput.value;
        // Regex to extract Cookie header value
        const cookieMatch = curlText.match(/-H\\s+'Cookie:\\s*([^']+)'/);
        if (cookieMatch && cookieMatch[1]) {
          document.getElementById("cookie").value = cookieMatch[1].trim();
        }
        // Regex to extract employeeId in JSON payload (--data-binary)
        const employeeIdMatch = curlText.match(/"employeeId"\\s*:\\s*(\\d+)/);
        if (employeeIdMatch && employeeIdMatch[1]) {
          document.getElementById("employee_id").value = employeeIdMatch[1].trim();
        }
      });

      scheduleForm.addEventListener("submit", function(e) {
        e.preventDefault();
        // Validation: ensure all required fields are filled
        const employeeId = document.getElementById("employee_id").value.trim();
        const cookie = document.getElementById("cookie").value.trim();
        const year = document.querySelector("input[name='year']").value.trim();
        const month = document.querySelector("input[name='month']").value.trim();
        if (!employeeId || !cookie || !year || !month) {
          alert("Please fill in all fields before scheduling.");
          return;
        }
        logsDiv.innerText = "";
        // Reveal stop button once scheduling starts
        stopForm.style.display = "block";
        const formData = new FormData(scheduleForm);
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
    employee_id = int(request.form["employee_id"])
    cookie = request.form["cookie"]
    year = int(request.form["year"])
    month = int(request.form["month"])
    
    q = queue.Queue()
    scheduler_stop_event = threading.Event()

    # Updated logger now adds a timestamp to every log line
    def logger(msg):
        timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        q.put(f"{timestamp} {msg}\n")

    def run_scheduler():
        result = schedule_month_shifts(employee_id, year, month, cookie, logger=logger, stop_event=scheduler_stop_event)
        q.put("FINAL_RESULT:" + json.dumps(result, indent=2))
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
