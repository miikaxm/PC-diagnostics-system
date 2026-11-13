# Funktio importit
from engine.inventory import (
    collect_hardware_info,
    save_hardware_info
)

from engine.test_manager import (
    run_tests,
    save_test_results
)

# Pääfunktio
def main():
    # Perus printit
    print("Tietokoneen vianmääritys")
  
    print("\nKerätään laitteistotietoja...")

    # Haetaan koneen tiedot "information" parametriin "collec_hardware_info" funktion avulla
    # Tallennetaan laitteisto tiedot JSON tiedostoon polkuun: #:\#\#\#\PC-Diagnostics\data\hardware_info.json ja palautetaan polku muuttujaan
    information = collect_hardware_info()
    hardware_file = save_hardware_info(information)

    # Printataan laitteistotietojen JSON tiedoston polku
    print(f"Laitteistotiedot: {hardware_file}")
    print("\nSuoritetaan tarkistukset...")

    # Ajetaan testit testimoottorin "run_tests" funktion avulla
    test_run = run_tests()

    # Printataan jokaisen testit tulokset (testin nimi, testin tulos eli PASS, FAIL, WARNING yms. ja testin tuloksen viesti)
    for result in test_run["results"]:
        print(
            f"{result['test_name']}: "
            f"{result['status']} - {result['message']}"
        )

    # Tallennetaan testien tulokset ja tallennetaan polku muuttujaan
    results_file = save_test_results(test_run)

    # Printataan testituloksien JSON tiedoston polku
    print(f"\nTestitulokset: {results_file}")


if __name__ == "__main__":
    main()