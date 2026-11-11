from engine.inventory import (
    collect_hardware_info,
    save_hardware_info
)


def main():
    print("PC Diagnotics")
    print("Versio: 0.2.0")

    print("\nKerätään laitteistotietoja...")

    information = collect_hardware_info()

    print("\nTietokoneen tiedot:")
    for key, value in information.items():
        print(f"{key}: {value}")

    filename = save_hardware_info(information)

    print(f"\nTiedot tallennettu: {filename}")


if __name__ == "__main__":
    main()
