
# Importit
import json
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

# Databasen osoite
DATABASE_PATH = (
  Path(__file__).resolve().parent.parent
  / "data"
  / "pc_diagnostics.db"
)

# Tietokannan ja taulujen luonti
def init_database():
  # Luodaan data kansio jos sitä ei vielä ole olemassa
  DATABASE_PATH.parent.mkdir(
    parents=True,
    exist_ok=True
  )

  # Avataan yhteys SQLite tietokantaan
  # closing sulkee yhteyden funktion lopuksi
  with closing(sqlite3.connect(DATABASE_PATH)) as connection:

    # Otetaan käyttöön tietokannan viiteavaimet
    # Näin testitulokset voidaan yhdistää oikeisiin testikertoihin
    connection.execute("PRAGMA foreign_keys = ON")

    # Tietokantamuutokset tallennetaan yhtenä tapahtumana
    with connection:

      # Luodaan taulut jos niitä ei vielä ole olemassa
      connection.executescript("""
        CREATE TABLE IF NOT EXISTS computers (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          hostname TEXT,
          hardware_json TEXT NOT NULL,
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS test_runs (
          run_id TEXT PRIMARY KEY,
          computer_id INTEGER NOT NULL,
          started_at TEXT NOT NULL,
          finished_at TEXT NOT NULL,
          status TEXT NOT NULL,
          FOREIGN KEY (computer_id)
            REFERENCES computers(id)
        );

        CREATE TABLE IF NOT EXISTS test_results (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          run_id TEXT NOT NULL,
          position INTEGER NOT NULL,
          test_id TEXT NOT NULL,
          test_name TEXT NOT NULL,
          status TEXT NOT NULL,
          message TEXT NOT NULL,
          details_json TEXT NOT NULL,
          FOREIGN KEY (run_id)
            REFERENCES test_runs(run_id)
        );

        CREATE INDEX IF NOT EXISTS idx_runs_started
          ON test_runs(started_at);

        CREATE INDEX IF NOT EXISTS idx_results_run
          ON test_results(run_id, position);
      """)

# Testin yhteenvedon määritys
def get_overall_status(results):
  # Jos testituloksia ei ole palautetaan UNKNOWN
  if not results:
    return "UNKNOWN"

  # Kerätään kaikkien testien tilat yhteen joukkoon
  statuses = {
    result.get("status", "UNKNOWN")
    for result in results
  }

  # Jos yksikin testi epäonnistui palautetaan FAIL
  if "FAIL" in statuses:
    return "FAIL"

  # Jos tuloksissa on varoitus palautetaan WARNING
  if "WARNING" in statuses:
    return "WARNING"

  # Jos jonkin testin tulosta ei tiedetä palautetaan UNKNOWN
  if "UNKNOWN" in statuses:
    return "UNKNOWN"

  # Jos kaikki testit onnistuivat palautetaan PASS
  if statuses == {"PASS"}:
    return "PASS"

  # Jos mitään tunnettua tilaa ei löytynyt palautetaan UNKNOWN
  return "UNKNOWN"

# Tallentaa testit ja niiden tulokset
def save_test_run(test_run, hardware_info=None):
  # Varmistetaan että tietokanta ja taulut ovat olemassa
  init_database()

  # Jos laitteistotietoja ei annettu käytetään tyhjää sanakirjaa
  hardware_info = hardware_info or {}

  # Haetaan testikerran yksittäiset tulokset
  results = test_run.get("results", [])

  # Varmistetaan että testitulokset ovat listamuodossa
  if not isinstance(results, list):
    raise ValueError("Testitulokset eivät ole lista")

  # Haetaan testikerran yksilöllinen tunniste
  run_id = test_run["run_id"]

  # Haetaan testikerran aloitusaika
  started_at = test_run["timestamp"]

  # Tallennetaan nykyinen aika testikerran lopetusajaksi
  finished_at = datetime.now().astimezone().isoformat()

  # Lasketaan kaikkien testien yhteinen lopputila
  overall_status = get_overall_status(results)

  # Haetaan tietokoneen nimi laitteistotiedoista
  hostname = hardware_info.get(
    "basic", {}
  ).get("hostname")

  # Avataan yhteys tietokantaan
  with closing(sqlite3.connect(DATABASE_PATH)) as connection:

    # Otetaan käyttöön viiteavainten tarkistus
    connection.execute("PRAGMA foreign_keys = ON")

    # Tallennetaan kaikki tiedot samassa tietokantatapahtumassa
    with connection:

      # Lisätään testattavan tietokoneen tiedot computers-tauluun
      cursor = connection.execute(
        """
        INSERT INTO computers (
          hostname,
          hardware_json,
          created_at
        )
        VALUES (?, ?, ?)
        """,
        (
          hostname,

          # Muutetaan laitteistotiedot JSON-merkkijonoksi
          json.dumps(
            hardware_info,
            ensure_ascii=False
          ),

          started_at
        )
      )

      # Otetaan talteen juuri lisätyn tietokoneen tunniste
      computer_id = cursor.lastrowid

      # Tallennetaan testikerran tiedot test_runs-tauluun
      # computer_id yhdistää testikerran tietokoneeseen
      connection.execute(
        """
        INSERT INTO test_runs (
          run_id,
          computer_id,
          started_at,
          finished_at,
          status
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
          run_id,
          computer_id,
          started_at,
          finished_at,
          overall_status
        )
      )

      # Käydään kaikki testikerran yksittäiset tulokset läpi
      # position kertoo missä järjestyksessä testit suoritettiin
      for position, result in enumerate(results):

        # Tallennetaan jokaisen testin tulos omaan riviinsä
        connection.execute(
          """
          INSERT INTO test_results (
            run_id,
            position,
            test_id,
            test_name,
            status,
            message,
            details_json
          )
          VALUES (?, ?, ?, ?, ?, ?, ?)
          """,
          (
            run_id,
            position,

            # Testin tunniste esimerkiksi cpu_stress tai smart
            result.get("test_id", "unknown"),

            # Testin nimi käyttöliittymää varten
            result.get("test_name", "Tuntematon testi"),

            # Testin lopputila
            result.get("status", "UNKNOWN"),

            # Testin palauttama viesti
            result.get("message", ""),

            # Muutetaan testin tarkemmat tiedot JSON-muotoon
            json.dumps(
              result.get("details", {}),
              ensure_ascii=False
            )
          )
        )

  # Palautetaan tallennetun testikerran tunniste
  return run_id


def list_test_runs(limit=50):
  # Varmistetaan että tietokanta on olemassa
  init_database()

  # Rajoitetaan haettavien testikertojen määrä välille 1-100
  limit = max(1, min(int(limit), 100))

  # Avataan yhteys tietokantaan
  with closing(sqlite3.connect(DATABASE_PATH)) as connection:

    # Mahdollistetaan tietojen hakeminen sarakkeiden nimillä
    connection.row_factory = sqlite3.Row

    # Haetaan testikerrat uusimmasta vanhimpaan
    # COUNT laskee kuinka monta yksittäistä testiä suoritettiin
    rows = connection.execute(
      """
      SELECT
        test_runs.run_id,
        test_runs.started_at,
        test_runs.finished_at,
        test_runs.status,
        computers.hostname,
        COUNT(test_results.id) AS test_count
      FROM test_runs
      JOIN computers
        ON computers.id = test_runs.computer_id
      LEFT JOIN test_results
        ON test_results.run_id = test_runs.run_id
      GROUP BY test_runs.run_id
      ORDER BY test_runs.started_at DESC
      LIMIT ?
      """,
      (limit,)
    ).fetchall()

  # Muutetaan tietokantarivit Python-sanakirjoiksi
  return [dict(row) for row in rows]


def get_test_run(run_id):
  # Varmistetaan että tietokanta on olemassa
  init_database()

  # Avataan yhteys SQLite-tietokantaan
  with closing(sqlite3.connect(DATABASE_PATH)) as connection:

    # Mahdollistetaan sarakkeiden käyttäminen nimillä
    connection.row_factory = sqlite3.Row

    # Etsitään tietty testikerta sen run_id-tunnisteella
    run = connection.execute(
      """
      SELECT
        test_runs.run_id,
        test_runs.started_at,
        test_runs.finished_at,
        test_runs.status,
        computers.hostname,
        computers.hardware_json
      FROM test_runs
      JOIN computers
        ON computers.id = test_runs.computer_id
      WHERE test_runs.run_id = ?
      """,
      (run_id,)
    ).fetchone()

    # Jos testikertaa ei löydy palautetaan None
    if run is None:
      return None

    # Haetaan kyseiseen testikertaan kuuluvat testitulokset
    # ORDER BY position säilyttää testien suoritusjärjestyksen
    result_rows = connection.execute(
      """
      SELECT
        test_id,
        test_name,
        status,
        message,
        details_json
      FROM test_results
      WHERE run_id = ?
      ORDER BY position
      """,
      (run_id,)
    ).fetchall()

  # Muodostetaan testikerran tiedoista yksi sanakirja
  return {
    "run_id": run["run_id"],
    "timestamp": run["started_at"],
    "finished_at": run["finished_at"],
    "status": run["status"],
    "hostname": run["hostname"],

    # Muutetaan tallennetut laitteistotiedot takaisin sanakirjaksi
    "hardware": json.loads(run["hardware_json"]),

    # Muodostetaan lista testikerran yksittäisistä tuloksista
    "results": [
      {
        "test_id": row["test_id"],
        "test_name": row["test_name"],
        "status": row["status"],
        "message": row["message"],

        # Muutetaan testin tarkemmat tiedot takaisin JSONista
        "details": json.loads(row["details_json"])
      }
      for row in result_rows
    ]
  }