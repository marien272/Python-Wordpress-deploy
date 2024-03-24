"""Ce projet a pour but de déployer automatiquement un environnement Apache2 et PHP7.2 ainsi que l'installation d'un serveur Wordpress. Ce script est prévu pour fonctionnement sous un environnement Debian 9."""
"""Copyright 2019 Dommery Anthony, licence Apache 2.0"""
"""Pour plus d'informations sur le script, lire le fichier README.md"""

"""Import des modules Python"""
import subprocess
from pip._internal import main as pip
import shutil
import pwd
import grp
import os
import tarfile
import sys
import time
try:
    import wget
except ImportError:
    pip(['install', 'wget'])
    time.sleep(10)
    import wget
try:
    import yaml
except ImportError:
    pip(['install', 'pyyaml'])
    time.sleep(10)
    import yaml
try:
    import pymysql
except ImportError:
    pip(['install', 'pymysql'])
    time.sleep(10)
    import pymysql
pymysql.install_as_MySQLdb()
import MySQLdb

"""Définition des variables globales"""
CONFDATA = ""

 
        
def readYamlConfig():
    """Fonction de lecture du fichier YAML et vérification des erreurs"""
    with open('config.yaml','r') as configFile:
        try:
            global CONFDATA
            """Chargement du fichier de configuration"""
            yamlData = yaml.load(configFile)
            """Copie des informations dans la variable globale CONFDATA"""
            CONFDATA = yamlData
        except yaml.YAMLError as exc:
            print(exc)
            sys.exit(1)
            

def updateApt():
    """Mise à jour de l'apt-get"""
    try:
        subprocess.call(['sudo apt-get update'], shell=True)
    except OSError:
        print ("Une erreur s'est produit lors de la mise à jour des paquets")
        sys.exit(2)


def apt_get_install(package_list):
    """Téléchargement et installation des paquets demandés"""

    for package in package_list:
        try:
            subprocess.call(['sudo apt-get install -y '+package], shell=True)
        except (OSError) as e:
            print ("Une erreur s'est produit lors de l'installation du paquet "+package)
            print (e)
            sys.exit(3)

def stateService(state, service_name):
    """Modification de l'état du service (start, restart, enable, stop...)"""
    try:
        subprocess.call(['sudo systemctl '+state+' '+service_name], shell=True)
    except (OSError) as e:
        print("Une erreur s'est produite lors de la modification d'état du service "+service_name)
        print (e)

class ApacheElem:
    """Class ApacheElem contenant les méthodes liées à Apache2"""
    def __init__(self, repository, paquets, documentConfName):
        self.repository = repository
        self.paquets = paquets
        self.documentConfName = documentConfName
    def installApache(self):
        """Installation du service via l'apt-get"""
        apt_get_install(self.paquets)
    
    def startApache(self):
        """Démarrage du service"""
        stateService('start','apache2.service')
        
    def configurationApache(self):
        global CONFDATA
        """Modifier le fichier avec le fichier de conf avant de le copier"""
        try:
            """Création d'une variable contenant le fichier de configuration Apache"""
            apacheConfExample = open(CONFDATA['apache']['configurationFile'],"r")
        except:
            print('Impossible d\'ouvrir le fichier template indiqué')
            sys.exit(4)
        apacheConfVariable = apacheConfExample.read()
        """Ecriture des données dans le fichier de configuration Apache"""
        apacheConfVariableModify = apacheConfVariable.replace('_SERVERNAME_',CONFDATA['apache']['ServerName']).replace('_SERVERALIAS_',CONFDATA['apache']['ServerAlias']).replace('_SERVERADMIN_',CONFDATA['apache']['ServerAdmin']).replace('_DOCUMENTROOT_',CONFDATA['apache']['DocumentRoot'])
        try:
            apacheConf = open("/etc/apache2/sites-available/"+self.documentConfName,"w+")
        except:
            print('Impossible d\'ouvrir le fichier apache indiqué')
            sys.exit(5)
        """Ecriture des infos dans le fichier de configuration Apache créé"""
        apacheConf.write(apacheConfVariableModify)
        apacheConfExample.close()
        apacheConf.close()
    
    def enableApacheConfiguration(self):
        try:
            print('a2ensite '+self.documentConfName)
            subprocess.call(['sudo a2ensite '+self.documentConfName], shell=True)
        except OSError:
            print ("Une erreur s'est produit lors de l'autorisation du fichier de configuration Apache")
            sys.exit(6)
    


class PhpElem:
    """Class PhpElem contenant les méthodes liées à PHP"""
    def __init__(self, paquets):
        self.paquets = paquets
    def installPhp(self):
        """Installation du service PHP 7.2"""
        apt_get_install(['ca-certificates', 'apt-transport-https', 'lsb-release'])
        try:
            subprocess.call(['wget -O /etc/apt/trusted.gpg.d/php.gpg https://packages.sury.org/php/apt.gpg'],shell=True)
            subprocess.call(['echo "deb https://packages.sury.org/php/ $(lsb_release -sc) main" > /etc/apt/sources.list.d/php.list'],shell=True)
        except OSError:
            print("Une erreur s'est produite lors de l'ajout du paquet d'installation php")
            sys.exit(7)
        updateApt()
        apt_get_install(self.paquets)
        
    def configurationPhp(self):
        """Configuration de PHP"""
        phpIniTemplate= open("configuration_files/php.ini","r")
        phpIni= open("/etc/php/7.2/apache2/php.ini","w")
        phpIni.write(phpIniTemplate.read())
        phpIni.close()
        phpIniTemplate.close()

class MariaDbElem:
    """Class MariaDbElem contenant les méthodes liées à la base de données"""
    def __init__(self, password, wpdb, wpuser, wppassword, paquets):
        self.password = password
        self.wpdb = wpdb
        self.wpuser = wpuser
        self.wppassword = wppassword
        self.paquets = paquets
                    
    def installMariaDb(self):
        """Installation du service via l'apt-get"""
        apt_get_install(self.paquets)
    

    def secureDbInstallation(self):
        """Sécurisation de la BD"""
        print(self.password)
        test = 'mysql -e "UPDATE mysql.user SET Password = PASSWORD(\''+self.password+'\') WHERE User = \'root\'"'
        print(test)
        try:
            subprocess.call([test],shell=True)
        except OSError:
            print("Une erreur s'est produite lors de la modification du compte root")
            sys.exit(8)
        try:
            subprocess.call(['sudo mysql -e "DELETE FROM mysql.user WHERE user=\'root\' AND host NOT IN (\'localhost\', \'127.0.0.1\', \'::1\')"'],shell=True)
        except OSError:
            print("Une erreur s'est produite lors de la suppression des comptes anonymes")
            sys.exit(8)
        try:
            subprocess.call(['sudo mysql -e "UPDATE mysql.user SET plugin=\'\' WHERE user=\'root\'"'],shell=True)
        except OSError:
            print("Une erreur s'est produite lors de la suppression des comptes anonymes")
            sys.exit(8)
        try:
            subprocess.call(['sudo mysql -e "DELETE FROM mysql.user WHERE user=\'\'"'],shell=True)
        except OSError:
            print("Une erreur s'est produite lors de la suppression des comptes anonymes")
            sys.exit(8)
        try:
            subprocess.call(['sudo mysql -e "DROP DATABASE test"'],shell=True)
        except OSError:
            print("Une erreur s'est produite lors de la suppression de la BDD test")
            sys.exit(8)
        try:
            subprocess.call(['sudo mysql -e "FLUSH PRIVILEGES"'],shell=True)
        except OSError:
            print("Une erreur s'est produite lors de l'attribution des privilèges")
            sys.exit(8)


    
    def createWpDataBase(self):
        """Fonction permettant de créer la BD Wordpress"""
        """Connexion à la base de données"""
        paramMysql = {
            "host" : "localhost",
            "user" : "root",
            "passwd" : self.password,
            "db" : "mysql",
        }
        """Requêtes SQL pour modification de la BDD"""
        queries = [
            'CREATE DATABASE IF NOT EXISTS '+self.wpdb+';',
            "CREATE USER "+self.wpuser+" IDENTIFIED BY '"+self.wppassword+"';",
            'GRANT ALL ON '+self.wpdb+'.* TO '+self.wpuser+' IDENTIFIED BY \''+self.wppassword+'\' WITH GRANT OPTION;',
            'FLUSH PRIVILEGES;']
        print(queries)
        
        try:
            conn = MySQLdb.connect(**paramMysql)
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            for querie in queries:
                cur.execute(querie)           
        except (MySQLdb.Error) as e:
            print ("Error %d: %s" % (e.args[0],e.args[1]))
            sys.exit(9)

class WordpressElem:
    """Class WordpressElem contenant les méthodes liées à Wordpress"""
    def __init__(self, documentRoot, urlDl, fileName):
        self.documentRoot = documentRoot
        self.urlDl = urlDl
        self.fileName = fileName
    """Installation de Wordpress dans le dossier défini dans le dossier de configuration"""
    def downloadWp(self):
        """Création de variables pour la localisation sur le serveur"""
        tempDir = CONFDATA['wordpress']['tempDir']
        currentDir = os.getcwd()
        try:
            """Création du dossier Wordpress"""
            if not os.path.exists(self.documentRoot):
                os.mkdir(self.documentRoot)
        except OSError:
            print ("Creation of the directory %s failed" % path)
            sys.exit(10)
        try:
            os.chdir(tempDir)
        except OSError:
            print("Une erreur s'est produite lors de l'acces au dossier "+tempDir)
        try:
            """Téléchargement du dossier Wordpress"""
            wget.download(self.urlDl, tempDir+'/'+self.fileName)
        except :
            print("Une erreur s'est produite lors du téléchargement de Wordpress")
            sys.exit(11)
        try:
            """Extraction de Wordpress"""
            tar = tarfile.open(tempDir+'/'+self.fileName, "r:gz")
            tar.extractall()
            tar.close()
        except :
            print("Une erreur s'est produite lors de l'extraction de Wordpress")
            sys.exit(12)
        try:
            """Déplacement des fichiers téléchargés dans le dossier Wordpress"""
            files = os.listdir(tempDir+'/wordpress')
            for f in files:
                shutil.move(tempDir+'/wordpress/'+f, self.documentRoot)
        except OSError:
            print("Une erreur s'est produite lors du déplacement du dossier Wordpress au répertoire défini")
            sys.exit(13)
        try:
            """Ajout des droits nécessaires aux dossiers et fichiers Wordpress"""
            os.chown(self.documentRoot,pwd.getpwnam("www-data").pw_uid,grp.getgrnam("www-data").gr_gid)
            os.chmod(self.documentRoot, 0o755)
            for root, dirs, files in os.walk(self.documentRoot):
                for d in dirs:
                    os.chmod(os.path.join(root, d), 0o755)
                    os.chown(os.path.join(root, d), pwd.getpwnam("www-data").pw_uid,grp.getgrnam("www-data").gr_gid)
                for f in files:
                    os.chown(os.path.join(root, f), pwd.getpwnam("www-data").pw_uid,grp.getgrnam("www-data").gr_gid)
                    os.chmod(os.path.join(root, f), 0o755)
        except OSError:
            print("Une erreur s'est produite lors de la modification des droits du dossier")
            sys.exit(14)
        try:
            os.chdir(currentDir)
        except OSError:
            print("Une erreur s'est produite lors de l'acces au dossier "+currentDir)
            sys.exit(15)



def main():
    readYamlConfig()
    updateApt()
    apache = ApacheElem(CONFDATA['apache']['DocumentRoot'], CONFDATA['apache']['paquets'],CONFDATA['apache']['DocumentConfName'])
    apache.installApache()
    apache.startApache()
    mariaDb = MariaDbElem(CONFDATA['sql']['rootPassword'], CONFDATA['sql']['wordpressDbName'], CONFDATA['sql']['wordpressUser'], CONFDATA['sql']['wordpressUserPassword'], CONFDATA['sql']['paquets'])
    mariaDb.installMariaDb()
    mariaDb.secureDbInstallation()
    php = PhpElem(CONFDATA['php']['paquets'])
    php.installPhp()
    mariaDb.createWpDataBase()
    wordpress = WordpressElem(CONFDATA['apache']['DocumentRoot'], CONFDATA['wordpress']['url'], CONFDATA['wordpress']['fileName'])
    wordpress.downloadWp()
    apache.configurationApache()
    apache.enableApacheConfiguration()
    stateService('reload','apache2')
    
main()