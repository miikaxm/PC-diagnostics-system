from engine.inventory import (
    collect_hardware_info,
    save_hardware_info
)

from engine.test_manager import (
    run_tests,
    save_test_results
)


def main():
    print("Tietokoneen vianmääritys")
    print("Versio: 0.3.0")
  
    print("\nKerätään laitteistotietoja...")

    information = collect_hardware_info()
    hardware_file = save_hardware_info(information)

    print(f"Laitteistotiedot: {hardware_file}")
    print("\nSuoritetaan tarkistukset...")

    test_run = run_tests()

    for result in test_run["results"]:
        print(
            f"{result['test_name']}: "
            f"{result['status']} - {result['message']}"
        )

    results_file = save_test_results(test_run)

    print(f"\nTestitulokset: {results_file}")


if __name__ == "__main__":
    main()