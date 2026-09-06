from pyfade import Fade ,Colors 
import random, string

arcane = '''

                                          _____  _____ _   _  _   _ _____ ___________ _____ 
                                        |  __ \|  ___| \ | || \ | |_   _|_   _| ___ \  _  |
                                        | |  \/| |__ |  \| ||  \| | | |   | | | |_/ / | | |
                                        | | __ |  __|| . ` || . ` | | |   | | |    /| | | |
                                        | |_\ \| |___| |\  || |\  |_| |_  | | | |\ \\ \_/ /
                                        \____/\____/\_| \_/\_| \_/\___/  \_/ \_| \_|\___/ 
                                                       By Arcane                             
                                                                                                     
'''
print(Fade.Vertical(Colors.green_to_blue , arcane))












amount = int(input('Nombre de nitros à generer: '))
value = 1
while value <= amount: 
    code = "https://discord.gift/" + ('').join(random.choices(string.ascii_letters + string.digits, k=16))
    f = open('Codes.txt', "a+")
    f.write(f'{code}\n')
    f.close()
    print(f'Générer | {code}')
    value +=1
