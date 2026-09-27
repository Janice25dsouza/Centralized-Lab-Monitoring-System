# Centralized Laboratory Monitoring and Alert System - Server

## Server Setup

### Backend Setup

#### 1. Navigate to the server directory

```bash
cd major-project/server/server
```

#### 2. Remove the existing virtual environment (if any)

If a `venv` folder already exists, delete it from the project directory.

#### 3. Create and activate a new virtual environment

```bash
python -m venv venv
venv\Scripts\activate
```

#### 4. Install the required dependencies

```bash
pip install -r requirements.txt
```

#### 5. Run the backend server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

The backend server will run on port `8000`.

---

## Frontend Setup

### 1. Navigate to the dashboard directory

Open a **new terminal** and navigate to the dashboard directory:

```bash
cd major-project/server/dashboard
```

### 2. Check Node.js and npm installation

Check whether Node.js and npm are installed:

```bash
node --version
npm --version
```

If either command is not recognized, install **Node.js** and then verify the installation using the commands above.

### 3. Install frontend dependencies

```bash
npm install
```

### 4. Run the frontend

```bash
npm run dev
```

The dashboard will be available at the URL displayed in the terminal.

---

## Running the Server

The server consists of two components:

* **Backend:** FastAPI server running on port `8000`
* **Frontend:** React/Vite dashboard

Start the backend first:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Then, in a separate terminal, start the frontend:

```bash
npm run dev
```

Make sure the server PC and client PCs are connected to the same local network.
