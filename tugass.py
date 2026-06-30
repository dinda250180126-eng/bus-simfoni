try:
    angka1 = float(input("Masukkan angka pertama: "))
    angka2 = float(input("Masukkan angka kedua: "))

    hasil = angka1 / angka2

except ValueError:
    print("Error: Input harus berupa angka.")

except ZeroDivisionError:
    print("Error: Pembagi tidak boleh nol.")

else:
    print("Hasil pembagian =", hasil)

finally:
    print("Terima kasih telah menggunakan program.")