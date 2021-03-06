from tslearn.clustering import TimeSeriesKMeans
from tslearn.datasets import CachedDatasets
from tslearn.preprocessing import TimeSeriesScalerMeanVariance, TimeSeriesResampler
from tslearn.utils import to_time_series
from tslearn.utils import to_time_series_dataset
from utils.plot import Plot
from utils.geo import Geo
from utils import series_supp as ss
import pickle
import pandas as pd
from collections import Counter
from utils.statics_func import *

class ClusterTs:
    """Classe disposant des methodes de transformations et de manipulations des donnees a des fins de partitionnements

    classe mere de:
        * :class:`kmean`
        * :class:`kshape`

    Parameters:
        * ss : SeriesSupp
            instance du manager de series temporelles

    Variables:
        * ts: Array[[[float]]]
            les series temporelle au format desiree pour le clustering
        * ts_clust: Array[int]
            Chaque entier est selon son index le cluster auquel appartient l'index referant de *ts*
        * ts_name: Array[String]
            Nom de la serie temporelle, du capteur a sa granularite (annee, mois, semaine)
        * ss: SeriesSupp
            instance du manager de series temporelles
        * sampler: int
            Taille du sampling :func:`sampler`
        * ploter: :class:Plot
            Instance d'un objet d'affichage
        * n: int
            Nombre de cluster
        * capteurs_names: Array[String]
            Nom de la serie temporelle, du capteur a sa granularite (annee, mois, semaine) *Bientot supprime*
        * from_save: Bool
            True si les infos sont recuperees d'un cluster sauvegarde
        * proto: Array[[[float]]]
            Prototype de chaque cluster
        * last_readed: {Dict}
            Informations recuperer depuis le fichier 'Pickle' sauvegarde du cluster etudier
        * store_path: String
            Chemin vers le dossier de stockage des sauvegardes.
            N'est plus utilise depuis l'implementation d'une boite de dialogue pour la recherche de fichier de sauvegarde
        * name_file: String
            Chemin absolue vers fichier 'Pickle'
        * clust_name: String
            Nom de la technique de clustering de l'instance
        * metric: String
            Nom de la technique de clacul de distance de l'instance
        * geo: :class:Geo
            Instance Geo
        * cluster_by_name: {Dict}
            Clustering des series temporelles uniquement par le nom des capteurs sans redondance
        * cluster_by_fullname: {Dict}
            Clustering des series temporelles uniquement par le nom des capteurs et leurs granularite
        * size_min: int
            Taille minimale d'une serie pour etre garde lors du preprocessing
        * nb_capteur: {Dict}
            Clustering des series temporelles uniquement par le nom des capteurs redondance
        * nb_week: {Dict}
            Lors d'un decoupage en semaine, represente la redondance par capteur des semaines

    Example:
        See: Cluster_engine.ipynb

    Notes:
        *Dependencies*:
            - tslearn
            - pandas
            - Pickle
    """
    def __init__(self, ss):
        self.ts = None
        self.ts_clust = None
        self.ts_name = None
        self.ss = ss
        self.sampler = 168 # 24/d - 168/w - 744[31](720[30]-696[29]-672[28])/m - 8760(8784)/y
        self.ploter = Plot(self)
        self.n = 5
        self.capteurs_names = []
        self.from_save = False
        self.proto = []
        self.last_readed = {}
        self.store_path = "cluster/13_06/"
        self.name_file = None
        self.clust_name = "Master"
        self.metric = ""
        self.geo = Geo(self.ss.cwd)
        self.cluster_by_name = {}
        self.cluster_by_fullname = {}
        self.size_min = 0
        self.nb_capteur =[]
        self.nb_week = []
        #self.read_txt_line_info = {}


    def __repr__(self):
        """
        Representation de l'instance via une chaine de caracteres explicative.

        Parameters:
            NA

        Returns:
            my_repr : str
                representation.
        """
        my_repr = ["Algorithm de clustering: " + self.clust_name, "Metric mesure: " + self.metric, "Espace de stockage: " + self.store_path, "Nombre de Clusters: " + str(self.n), "Sampler de taille : " + str(self.sampler)]
        return '\n'.join('%s' % v for v in my_repr)

    def tslearn_format_export(self, other_data = None):
        """
        Export la variable data vers le format utilise par tslearn pour la partitionnements

        Parameters:
            NA

        Returns::
            NA
        """
        df = []
        dn = []
        if self.ss.days:
            size_max = 170
        else:
            size_max = 750
        if other_data != None:
            data_dict = other_data
        else:
            data_dict = self.ss.get_data()
        for k, v in data_dict.items():
            if not self.check_equal(v["Valeur"].values):
                if len(v["Valeur"].values) > self.size_min and len(v["Valeur"].values) < size_max:
                    df.append(v["Valeur"].values)
                    dn.append(k)
                    self.capteurs_names.append(k)
        df_set = to_time_series_dataset(df)
        if self.sampler != 0:
            df_set = TimeSeriesResampler(self.sampler).fit_transform(df_set)
        self.ts = df_set
        self.ts_name = dn

    def set_size_min(self, size):
        """
        Set taille minimale d'une TS pour etre gardee

        Parameters:
            * size: int
                Taille minimale

        Returns:
            NA
        """
        self.size_min = size

    def check_equal(self, iterator):
        """
        Verifie si la TS reste tout le temps sur la meme valeur

        Parameters:
            * iterator: iterator
                la TS

        Returns:
            Bool
        """
        iterator = iter(iterator)
        try:
            first = next(iterator)
        except StopIteration:
            return True
        return all(first == rest for rest in iterator)

    def show_info(self):
        """
        Affiche les informations recuperees depuis le txt d'info de la sauvegarde cluster lie a l'instance

        Parameters:
            NA

        Returns:
            NA
        """
        file = open(str(self.name_file[:-4]) + ".txt", "r")
        print (file.read())
        file.close()
        #i = 0
        #with open(str(self.store_path) + str(self.name_file) + ".txt", "r") as f:
        #    self.read_txt_line_info[i] = f.readlines()
        #    i += 1

    def store_cluster(self, name):
        """
        Sauvegarde sur forme de fichier pickle associe a un txt d'information la partitionnement actuelle de l'instance

        Parameters:
            * name: String
                Nom du fichier, represente les parametre principaux de la partitionnement

        Returns:
            NA
        """
        info_dict = {}
        info_dict["trace"] = self.ts
        info_dict["classe"] = self.ts_clust
        info_dict["name"] = self.ts_name
        info_dict["proto"] = self.km.cluster_centers_
        info_dict["sample"] = self.sampler
        info_dict["years"] = self.ss.years
        info_dict["months"] = self.ss.months
        info_dict["days"] = self.ss.days
        info_dict["size_min"] = self.size_min
        info_dict["round"] = self.ss.rounded
        info_dict["smoothed"] = self.ss.smoothed

        outfile = open(self.store_path + name + ".pkl", "wb")
        pickle.dump(info_dict, outfile)
        outfile.close()

        file = open(self.store_path + name + ".txt", "w")
        file.write(str([i for i in self.ss.years]) + "\n")
        file.write(str([i for i in self.ss.months]) + "\n")
        file.write("Weeks split: " + str(self.ss.days) + "\n")
        file.write("Normalized: " + str(self.ss.norm) + "\n")
        file.write("min size of TS selected: " + str(self.size_min) + "\n")
        file.write("Sample size(0=None): " + str(self.sampler) + "\n")
        file.write("Algorithm used: " + str(self.clust_name) + "\n")
        file.write("nb cluster: " + str(self.n) + "\n")
        file.write("Distance measure: " + str(self.metric) + "\n")
        file.write("Rounded values: " + str(self.ss.rounded) +"\n")
        file.write("smoothed values: " + str(self.ss.smoothed) +"\n")
        file.close()

    def read_cluster(self, path = ""):
        """
        Ouvre et recupere toutes les informations d'un fichier pickle(sauvegarde d'un clustering) et update les variable de l'instance pour correspondre

        Parameters:
            * path: String
                Chemin d'acces au fichier

        Returns:
            NA
        """
        infile = open(str(path),'rb')
        info_dict = pickle.load(infile)
        infile.close()
        self.store_path = path
        self.name_file = path
        self.ts = info_dict["trace"]
        self.ts_clust = info_dict["classe"]
        self.ts_name = info_dict["name"]
        self.capteurs_names = info_dict["name"]
        self.proto = info_dict["proto"]
        self.n = len(info_dict["proto"])
        self.sampler = info_dict["sample"]
        self.from_save = True
        self.last_readed = info_dict
        try:
            self.ss.years = info_dict["years"]
            self.ss.months = info_dict["months"]
            self.ss.days = info_dict["days"]
        except:
            pass
        try:
            self.ss.rounded = info_dict["round"]
        except:
            self.ss.rounded = "no information"
        try:
            self.ss.smoothed = info_dict["smoothed"]
        except:
            self.ss.smoothed = "no information"

    def get_cluster_n(self, n):
        """
        Retourne les TS d'un cluster **n**

        Parameters:
            * n: int
                Numero de cluster souhaite

        Returns:
            res: Array[float]
                Ensemble des TS du cluster
        """
        res = []
        for xx in self.ts[self.ts_clust == n]:
            res.append(xx)
        return res

    def capteur_parser(self):
        """
        Parser des noms de capteurs, pour pouvoir garder en memoire les nom des capteur et leur extension de date selon la TS

        Parameters:
            NA

        Returns:
            NA
        """
        res = {}
        res_full = {}
        nb_capteur = {}
        nb_week = {}
        for i in range(0, self.n):
            res[i], res_full[i], nb_capteur[i], nb_week[i] = [], [], [], []
        for elmt in self.ts_name:
            non_parse = str(elmt)
            parse = str(elmt[0:2] + elmt[3:6])
            if parse not in res[self.ts_clust[self.ts_name.index(elmt)]]:
                res[self.ts_clust[self.ts_name.index(elmt)]].append(parse)
            nb_capteur[self.ts_clust[self.ts_name.index(elmt)]].append(parse)
            nb_week[self.ts_clust[self.ts_name.index(elmt)]].append(elmt[-2:].replace("_", "0"))
            res_full[self.ts_clust[self.ts_name.index(elmt)]].append(non_parse)
        self.cluster_by_name = res
        self.cluster_by_fullname = res_full
        self.nb_capteur = nb_capteur
        self.nb_week = nb_week

    def get_part_of_ts(self, data, elmt):
        """
        Selon les Parameters d'elmt retrouve une partie des donnes depuis data

        Parameters:
            * data: {Dict}
                Donnee depuis les quelles on souhaite recuperer une partie precise
            * elmt: {Dict}
                Information liee a la demande (date)

        Returns:
            res_ts: Array[float]
                TS souhaitee
        """
        res_ts = data[elmt["capteur"]].copy()
        res_ts = res_ts.set_index("Date")
        if elmt["week"] and not elmt["month"]:
            res_ts = res_ts[str(elmt["year"])]
            res_ts = res_ts.groupby(pd.Grouper(freq='W'))
            for i in res_ts:
                if i[0].week == elmt["week"]:
                    res_ts = i[1]
        elif elmt["week"] and elmt["month"]:
            res_ts = res_ts[str(elmt["year"]) +"-"+ str(elmt["month"])]
            res_ts = res_ts.groupby(pd.Grouper(freq='W'))
            for i in res_ts:
                if i[0].week == elmt["week"]:
                    res_ts = i[1]
        elif elmt["month"]:
            res_ts = res_ts[str(elmt["year"]) +"-"+ str(elmt["month"])]
        else:
            res_ts = res_ts[str(elmt["month"])]
        res_ts = res_ts.reset_index()
        res_ts = self.ss.normalize(res_ts)
        return res_ts

    def clust_hoverview_rng(self, n):
        """
        DEPRECATED: Tire une TS random d'un cluster **n** pour se donner une idee des membres de ce dernier

        Parameters:
            * n: int
                Le cluster numero n

        Returns:
            NA
        """
        #r_RG, r_GW = ss.SeriesSupp(cwd, self.ss.factory, "RG24"), ss.SeriesSupp(cwd, factory, "GW")
        rng_elmt = self.cluster_by_fullname[n][0]
        elmt = self.parse_capteur_split(rng_elmt)
        gw = self.get_part_of_ts(self.ss.dataset, elmt)
        elmt2 = elmt.copy()
        elmt2["capteur"] = "24h_RG007" # EN DUR TROUVER LE PLUS PROCHE
        rg = self.get_part_of_ts(self.ss.factory.get_RG24(), elmt2)
        self.ploter.plot_single_scatter({elmt["capteur"]: gw, elmt2["capteur"]: rg})

    def clust_hoverview(self, n):
        """
        Affiche les TS d'un cluster **n** donnee

        Parameters:
            * n: int
                cluster selectionne

        Returns:
            NA
        """
        elmt_clust = self.cluster_by_fullname[n]
        all_clust_origin_ts = {}
        for elmt in elmt_clust:
            parse = self.parse_capteur_split(elmt)
            #print(parse)
            all_clust_origin_ts[elmt] = self.get_part_of_ts(self.ss.dataset, parse)
        self.ploter.plot_scatter(all_clust_origin_ts)

    def parse_capteur_split(self, elmt):
        """
        Recupere les information d'une TS depuis son nom comme le nom de son capteur et la date

        Parameters:
            * elmt: String
                Nom du capteur avec info

        Returns:
            res: {Dict}
                Les infos decoupes et range dans un dico
        """
        elmt = elmt.split("_")
        capteur = elmt[0] + "_" + elmt[1]
        year = int(elmt[2])
        if len(elmt) > 3 and not self.ss.days:
            month = int(elmt[3])
        else:
            month = 0
        if len(elmt) > 4:
            week = int(elmt[4])
        else:
            week = 0
        if len(elmt) > 3 and self.ss.days:
            week = int(elmt[3])
        else:
            week = 0
        res = {}
        res["capteur"], res["year"], res["month"], res["week"] = capteur, year, month, week
        return res

    def highlight_max(self, s):
        """
        Parametre d'affichage surligne les max par ligne de DataFrame

        Parameters:
            * s: pandas
                Ligne du tableau

        Returns:
            unnamed: pands.style
                Affichage des max
        """
        is_max = s == s.max()
        return ['background-color: red' if v else '' for v in is_max]

    def style_df(self, opt, t):
        if opt == "max":
            t_style = t.style.apply(self.highlight_max, axis = 1)
            return t_style

    def get_captor_distribution_in_cluster(self):
        """
        Retourne le nombre d'occurance des cpateur dans chacun des clusters

        Parameters:
            NA

        Returns:
            unnamed: DataFrame
                Tableau d'occurance
        """
        tot = {}
        for k, v in self.nb_capteur.items():
            tot[k] = Counter(v)
        return pd.DataFrame(tot)

    def get_ts_by_captor(self, cpt):
        """
        recupere les TS pour capteur **cpt** donne et leur distribution au sein des cluster

        Parameters:
            * cpt: String
                Capteur target

        Returns:
            res: tuple(String, {Dict})
                String represente le capteur et le dictionnaires la distribution des sous TS dans chaque clusters (key = cluster)
        """
        res = (cpt, {})
        i = 0
        for elmt in range(len(self.proto)):
            res[1][i] = []
            i += 1
        i = 0
        for string in self.ts_name:
            if cpt in string:
                res[1][self.ts_clust[i]].append([string, self.ts[i].ravel()])
            i += 1
        return res

    def get_clust_part_for_captor(self, cpt):
        """
        recupere les cluster pour capteur **cpt** donne et leur distribution au sein des cluster

        Parameters:
            * cpt: String
                Capteur target

        Returns:
            res: String
                Seulement les noms des date pour chacun des clusters
        """
        res = (cpt, {})
        i = 0
        for elmt in range(len(self.proto)):
            res[1][i] = []
            i += 1
        i = 0
        for string in self.ts_name:
            if cpt in string:
                res[1][self.ts_clust[i]].append(string)
            i += 1
        return res

    def aff_color(self):
        """
        Affiche les couleurs utilise dans le clustering
        """
        c = COLORS[:self.n + 1]
        df = pd.DataFrame({'colors':c})
        print(df.T)
