from django.db import models
from datetime import datetime


class Bi_wash(models.Model):
	date_time               = models.DateTimeField('Время совершения операции', default=datetime.now, blank=True)
	card_number				= models.CharField("Номер карты клиента", default='', null=True, max_length=150, blank=True)
	wash_id         		= models.IntegerField('ID', default = 0, null=True, blank=True)
	source_type            	= models.CharField("Источник или назначение платежа", default='', null=True, max_length=150, blank=True)
	source_number         	= models.IntegerField('Номер робота или терминала', default = 0, null=True, blank=True)
	dest_type            	= models.CharField("Источник или назначение платежа", default='', null=True, max_length=150, blank=True)
	dest_number            	= models.IntegerField('Номер робота или терминала', default = 0, null=True, blank=True)
	subject               	= models.CharField("Предмет", default='', null=True, max_length=512, blank=True)
	payment_type            = models.CharField("Назначение платежа", default='', null=True, max_length=512, blank=True)
	amount                  = models.FloatField("Количество затраченных средств", default = 0.0, null=True, blank=True)
    
	def __str__(self):
		return "{} {} - {} - {} - {}".format(self.date_time, self.subject, self.subject, self.dest_number, self.amount)

	class Meta:
		db_table = 'bi_wash'
		verbose_name = "Робомойки"
		verbose_name_plural = "Робомойки"
	

class Bi_logs(models.Model):
    bi_model                = models.CharField("Таблица", default='', null=True, max_length=150, blank=True)
    date                    = models.DateTimeField('Дата', default=datetime.now, blank=True)
    count_add               = models.IntegerField('Количество записей добавлено', default = 0, null=True, blank=True)
    count_delite            = models.IntegerField('Количество записей удалено', default = 0, null=True, blank=True)
    filtr                   = models.CharField("Отбор", max_length=512, null=True, blank=True)
    
    def __str__(self):
        return "{} ({} - {} - {}".format(self.date, self.bi_model, self.count_add, self.count_delite)

    class Meta:
        db_table = 'bi_logs'
        verbose_name = "Лог загрузки"
        verbose_name_plural = "Логи загрузки"


class mers_SQL(models.Model):
	VIN                         = models.CharField("VIN", max_length=150, null=True, blank=True)
	Administrator               = models.CharField("Administrator", max_length=150, null=True, blank=True)
	AdministratorDolznost       = models.CharField("AdministratorDolznost", max_length=150, null=True, blank=True)
	VidZakazNaryda              = models.CharField("VidZakazNaryda", max_length=150, null=True, blank=True)
	VyruchkaPoZapchastyam       = models.IntegerField("VyruchkaPoZapchastyam", default = 0, null=True, blank=True)
	GodVypuska                  = models.IntegerField("GodVypuska", default = 0, null=True, blank=True)
	GruppaPDC                   = models.CharField("GruppaPDC", max_length=150, null=True, blank=True)
	DataOtcrytiyaZN             = models.DateTimeField("DataOtcrytiyaZN", null=True, blank=True)
	Klient                      = models.CharField("Klient", max_length=150, null=True, blank=True)
	KolichestvoNCHPodryad       = models.CharField("KolichestvoNCHPodryad", max_length=150, null=True, blank=True)
	Marka                       = models.CharField("Marka", max_length=150, null=True, blank=True)
	MasterPriemshhik            = models.CharField("MasterPriemshhik", max_length=150, null=True, blank=True)
	MasterPriemshhikDolzhnost   = models.CharField("MasterPriemshhikDolzhnost", max_length=150, null=True, blank=True)
	Mashinozaezdy               = models.CharField("Mashinozaezdy", max_length=150, null=True, blank=True)
	Mexanik                     = models.CharField("Mexanik", max_length=150, null=True, blank=True)
	MexanikDolzhnost            = models.CharField("MexanikDolzhnost", max_length=150, null=True, blank=True)
	Model                       = models.CharField("Model", max_length=150, null=True, blank=True)
	Nomenclatura                = models.CharField("Nomenclatura", max_length=512, null=True, blank=True)
	Artikul                     = models.CharField("Artikul", max_length=150, null=True, blank=True)
	NomerZakazNaryada           = models.CharField("NomerZakazNaryada", max_length=150, null=True, blank=True)
	Normochasy                  = models.CharField("Normochasy", max_length=150, null=True, blank=True)
	Period                      = models.DateTimeField("Period", null=True, blank=True)
	Sebestoimost                = models.IntegerField("Sebestoimost", default = 0, null=True, blank=True)
	SummaSubpodryad             = models.IntegerField("SummaSubpodryad", default = 0, null=True, blank=True)
	PodrazdelenieDC             = models.CharField("PodrazdelenieDC", max_length=150, null=True, blank=True)
	Stoimost                    = models.CharField("Stoimost", max_length=150, null=True, blank=True)
	VidKontragent               = models.CharField("VidKontragent", max_length=150, null=True, blank=True)

	def __str__(self):
		return "{} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} ".format( self.VIN, self.Administrator, self.AdministratorDolznost, self.VidZakazNaryda, self.VyruchkaPoZapchastyam, self.GodVypuska, self.GruppaPDC, self.DataOtcrytiyaZN, self.Klient, self.KolichestvoNCHPodryad, self.Marka, self.MasterPriemshhik, self.MasterPriemshhikDolzhnost, self.Mashinozaezdy, self.Mexanik, self.MexanikDolzhnost, self.Model, self.Nomenclatura, self.Artikul, self.NomerZakazNaryada, self.Normochasy, self.Period, self.Sebestoimost, self.SummaSubpodryad, self.PodrazdelenieDC, self.Stoimost, self.VidKontragent,)  

	class Meta:
		db_table = 'mers_SQL'
		verbose_name = 'MercedesSQLДетали'
		verbose_name_plural = 'MercedesSQLДетали'


class StockTZK(models.Model):
    BL                          = models.IntegerField("ЧС", default = 0, null=True, blank=True)
    Cancel                      = models.IntegerField('Отказ', default = 0, null=True, blank=True)
    Cuality                     = models.IntegerField("Качество", default = 0, null=True, blank=True)
    DataOprosa                  = models.DateTimeField('ДатаОпроса', null=True, blank=True)
    DolgijRemont                = models.IntegerField('ДолгийРемонт', default = 0, null=True, blank=True)
    DorogoeObsluzhivanie        = models.IntegerField('ДорогоеОбслуживание', default = 0, null=True, blank=True)
    DovolnyeNegativaNet         = models.IntegerField('ДовольныеНегативаНет', default = 0, null=True, blank=True)
    feedback                    = models.IntegerField("ОбратнаяСвязь", default = 0, null=True, blank=True)
    IsService                   = models.IntegerField('Сервис', default = 0, null=True, blank=True)
    KachestvoRemonta            = models.IntegerField('КачествоРемонта', default = 0, null=True, blank=True)
    Kritiki                     = models.IntegerField("Критики", default = 0, null=True, blank=True)
    NedovolnyeKlienty           = models.IntegerField("НедовольныеКлиенты", default = 0, null=True, blank=True)
    Negative                    = models.CharField("КатегорияНегатива", max_length=150, null=True, blank=True)
    NegativNeSnyat              = models.IntegerField("НегативНеСнят", default = 0, null=True, blank=True)
    Nejtral                     = models.IntegerField("Нейтрал", default = 0, null=True, blank=True)
    NejtralOtkazOtOprosa        = models.IntegerField("НейтралОтказОтОпроса", default = 0, null=True, blank=True)
    NejtralyCHS                 = models.IntegerField("НейтралыЧС", default = 0, null=True, blank=True)
    nekorrRabotaPriemki         = models.IntegerField("некоррРаботаПриемки", default = 0, null=True, blank=True)
    NN_Nedovolki                = models.IntegerField("НН_Недовольки", default = 0, null=True, blank=True)
    NomerOprosa                 = models.CharField('НомерОпроса', max_length=150, null=True, blank=True)
    NPS                         = models.IntegerField("NPS", default = 0, null=True, blank=True)
    OproshenoKlientov           = models.IntegerField("ОпрошеноКлиентов", default = 0, null=True, blank=True)
    OprosNeProveden             = models.IntegerField('ОпросНеПроведен', default = 0, null=True, blank=True)
    OprosObrabotan              = models.IntegerField('ОпросОбработан', default = 0, null=True, blank=True)
    OtkazVGarantii              = models.IntegerField("ОтказВГарантии", default = 0, null=True, blank=True)
    OtsutstvieZCH               = models.IntegerField("ОтсутствиеЗЧ", default = 0, null=True, blank=True)
    Personal                    = models.IntegerField("Персонал", default = 0, null=True, blank=True)
    PodrazdelenieDC             = models.CharField("ПодразделениеДЦ", max_length=150, null=True, blank=True)
    Pokupka                     = models.IntegerField("Покупка",  default = 0, null=True, blank=True)
    PrinuditelnoeZakrytie       = models.IntegerField("ПринудительноеЗакрытие", default = 0, null=True, blank=True)
    Prochee                     = models.IntegerField("Прочее", default = 0, null=True, blank=True)
    Promouter                   = models.IntegerField("Промоутер", default = 0, null=True, blank=True)
    Q7                          = models.CharField("Вопрос7", max_length=150, null=True, blank=True)
    Qwest                       = models.CharField("Вопрос", max_length=150, null=True, blank=True)
    SpeedService                = models.IntegerField("СкоростьОбслуживания", default = 0, null=True, blank=True)
    TelefonNeOtvechaet          = models.IntegerField("ТелефонНеОтвечает", default = 0, null=True, blank=True)
    TradeIN                     = models.IntegerField("ТрейдИН", default = 0, null=True, blank=True)
    TZK                         = models.IntegerField("ТЗК", default = 0, null=True, blank=True)
    Vidacha                     = models.IntegerField("Выдача", default = 0, null=True, blank=True)
    VidKlienta                  = models.CharField("ВидКлиента", max_length=150, null=True, blank=True)
    VidOprosa                   = models.CharField("ВидОпроса", max_length=150, null=True, blank=True)
    VIN                         = models.CharField("VIN", max_length=150, null=True, blank=True)
    VRabote                     = models.IntegerField("ВРаботе", default = 0, null=True, blank=True)
    VsegoKlientovObsluzheno     = models.IntegerField("ВсегоКлиентовОбслужено", default = 0, null=True, blank=True)
    ZakrytOpros                 = models.IntegerField('ЗакрытОпрос', default = 0, null=True, blank=True)
    ZNData                      = models.DateTimeField('ДатаЗаказНаряда', null=True, blank=True)
    ZNNomer                     = models.CharField("НомерЗаказНаряда", max_length=150, null=True, blank=True)

    def __str__(self):
        return "{} ({} - {}".format(self.VIN, self.ZNData, self.ZNNomer)

    class Meta:
        db_table = 'StockTZK'
        verbose_name = "Сток ТЗК Плоская"
        verbose_name_plural = "Сток ТЗК Плоская"


class MKU_State_Orders(models.Model):
	Period              = models.DateTimeField("ДатаОтчета", null=True, blank=True)
	MZ_State            = models.CharField("СостояниеМЗ", max_length=150, null=True, blank=True)
	ZN_Number           = models.CharField("НомерЗН", max_length=150, null=True, blank=True)
	ZN_Date             = models.DateTimeField("ДатаЗН", null=True, blank=True)
	MZ_Number           = models.CharField("НомерМЗ", max_length=150, null=True, blank=True)
	MZ_Date             = models.DateTimeField("ДатаМЗ", null=True, blank=True)
	responisble_Person  = models.CharField("Ответственный", max_length=150, null=True, blank=True)
	Insurance_Referral  = models.CharField("НаправлениеНаРемонт", max_length=150, null=True, blank=True)
	Brand_Model         = models.CharField("Модель", max_length=150, null=True, blank=True)
	GosNumber           = models.CharField("ГосНомер", max_length=150, null=True, blank=True)
	Owner               = models.CharField("Собственник", max_length=150, null=True, blank=True)
	VIN                 = models.CharField("VIN", max_length=150, null=True, blank=True)
	Repair_Type         = models.CharField("ВидРемонта", max_length=150, null=True, blank=True)
	Parts_Ordered       = models.CharField("ЗапчастиЗаказаны", max_length=150, null=True, blank=True)
	Parts_Arriving_Date_Fact = models.DateTimeField("ДатаПоступленияЗапчастей", null=True, blank=True)
	ZN_Status           = models.CharField("СтатусЗН", max_length=150, null=True, blank=True)
	Normochasy          = models.IntegerField("КоличествоНЧ", default = 0, null=True, blank=True)
	Revenue_Works       = models.IntegerField("ВыручкаРаботы", default = 0, null=True, blank=True)
	Revenue_Parts       = models.IntegerField("ВыручкаЗЧ", default = 0, null=True, blank=True)
	Cost_LKM            = models.IntegerField("СебестоимостьЗЧ", default = 0, null=True, blank=True)
	Revenue_LKM         = models.IntegerField("ВыручкаРМЛКМ", default = 0, null=True, blank=True)
	Sum_Paid            = models.IntegerField("Оплата", default = 0, null=True, blank=True)
	Payer_Name          = models.CharField("Плательщик", max_length=150, null=True, blank=True)
	Payer_Group         = models.CharField("ГруппаПлательщика", max_length=150, null=True, blank=True)
	Last_Comment        = models.CharField("Комментарий", max_length=150, null=True, blank=True)
	PodrazdelenieDC     = models.CharField("Подразделение", max_length=150, null=True, blank=True)
	Last_Comment_Date   = models.DateTimeField("ДатаКомментария", null=True, blank=True)
	GRAFIK_Date         = models.DateTimeField("ДатаВГрафике", null=True, blank=True)
	VYDACHA_Date        = models.DateTimeField("ДатаВыдачи", null=True, blank=True)
	Osmotr              = models.CharField("Осмотрен", max_length=150, null=True, blank=True)
	Next_Month          = models.CharField("ВСледующийМесяц", max_length=150, null=True, blank=True)

	def __str__(self):
		return "{} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} ".format( self.Period, self.MZ_State, self.ZN_Number, self.ZN_Date, self.MZ_Number, self.MZ_Date, self.responisble_Person, self.Insurance_Referral, self.Brand_Model, self.GosNumber, self.Owner, self.VIN, self.Repair_Type, self.Parts_Ordered, self.Parts_Arriving_Date_Fact, self.ZN_Status, self.Normochasy, self.Revenue_Works, self.Revenue_Parts, self.Cost_LKM, self.Revenue_LKM, self.Sum_Paid, self.Payer_Name, self.Payer_Group, self.Last_Comment, self.PodrazdelenieDC, self.Last_Comment_Date, self.GRAFIK_Date, self.VYDACHA_Date, self.Osmotr, self.Next_Month,)  

	class Meta:
		db_table = 'MKU_State_Orders'
		verbose_name = 'СостояниеЗаказНарядовМКУ'
		verbose_name_plural = 'СостояниеЗаказНарядовМКУ'    


class EstimationOP(models.Model):
	OprosData               = models.DateTimeField("ОпросДата", null=True, blank=True)
	Akcii                   = models.IntegerField("Акции", default = 0, null=True, blank=True)
	VesVoprosa              = models.IntegerField("ВесВопроса", default = 0, null=True, blank=True)
	Vizity                  = models.IntegerField("Визиты", default = 0, null=True, blank=True)
	Vsego                   = models.IntegerField("Всего", default = 0, null=True, blank=True)
	GruppaPDC               = models.CharField("ГруппаПДЦ", max_length=150, null=True, blank=True)
	DSK                     = models.IntegerField("ДСК", default = 0, null=True, blank=True)
	EstKontaktnayaInformaciya   = models.IntegerField("ЕстьКонтактнаяИнформация", default = 0, null=True, blank=True)
	ZvonokBezOtveta             = models.IntegerField("ЗвонокБезОтвета", default = 0, null=True, blank=True)
	Logika                      = models.IntegerField("Логика", default = 0, null=True, blank=True)
	Menedzher               = models.CharField("Менеджер", max_length=150, null=True, blank=True)
	NePodlezhitOcenke       = models.IntegerField("НеПодлежитОценке", default = 0, null=True, blank=True)
	Opros                   = models.CharField("Опрос", max_length=150, null=True, blank=True)
	Oceneno                 = models.IntegerField("Оценено", default = 0, null=True, blank=True)
	OcenkaOtveta            = models.IntegerField("ОценкаОтвета", default = 0, null=True, blank=True)
	PervichnyjZvonok        = models.IntegerField("ПервичныйЗвонок", default = 0, null=True, blank=True)
	Perezvonili             = models.IntegerField("Перезвонили", default = 0, null=True, blank=True)
	PodrazdelenieDC         = models.CharField("ПодразделениеДЦ", max_length=150, null=True, blank=True)
	Poryadok                = models.CharField("Порядок", max_length=150, null=True, blank=True)
	Potrebnosti             = models.IntegerField("Потребности", default = 0, null=True, blank=True)
	RabochijListData        = models.DateTimeField("РабочийЛистДата", null=True, blank=True)
	RabochijListNomer       = models.CharField("РабочийЛистНомер", max_length=150, null=True, blank=True)
	SozdanRL                = models.IntegerField("СозданРЛ", default = 0, null=True, blank=True)
	Cena                    = models.IntegerField("Цена", default = 0, null=True, blank=True)

	def __str__(self):
		return "{} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} ".format( self.OprosData, self.Akcii, self.VesVoprosa, self.Vizity, self.Vsego, self.GruppaPDC, self.DSK, self.EstKontaktnayaInformaciya, self.ZvonokBezOtveta, self.Logika, self.Menedzher, self.NePodlezhitOcenke, self.Opros, self.Oceneno, self.OcenkaOtveta, self.PervichnyjZvonok, self.Perezvonili, self.PodrazdelenieDC, self.Poryadok, self.Potrebnosti, self.RabochijListData, self.RabochijListNomer, self.SozdanRL, self.Cena,)  

	class Meta:
		db_table = 'EstimationOP'
		verbose_name = 'ПрослушкаОППлоский'
		verbose_name_plural = 'ПрослушкаОППлоский'


class CumulativeMarginUS(models.Model):
	OurCompany              = models.CharField("СобственнаяКомпания", max_length=150, null=True, blank=True)
	SoglashenieNomer        = models.CharField("СоглашениеНомер", max_length=150, null=True, blank=True)
	SoglashenieData         = models.DateTimeField("СоглашениеДата", null=True, blank=True)
	FilialPriema            = models.CharField("ФилиалПриема", max_length=150, null=True, blank=True)
	RRCPervonachalnaya      = models.IntegerField("РРЦПервоначальная", default = 0, null=True, blank=True)
	ListOcenkiKlientVidKontragenta  = models.CharField("ЛистОценкиКлиентВидКонтрагента", max_length=150, null=True, blank=True)
	ListOcenkiKlient        = models.CharField("ЛистОценкиКлиент", max_length=150, null=True, blank=True)
	SummaEkvajring          = models.IntegerField("СуммаЭквайринг", default = 0, null=True, blank=True)
	FaktAdres               = models.CharField("ФактАдрес", max_length=150, null=True, blank=True)
	VIN                     = models.CharField("VIN", max_length=150, null=True, blank=True)
	Adres                   = models.CharField("Адрес", max_length=150, null=True, blank=True)
	VidKontragenta          = models.CharField("ВидКонтрагента", max_length=150, null=True, blank=True)
	VPDopy                  = models.IntegerField("ВПДопы", default = 0, null=True, blank=True)
	VPKredit                = models.IntegerField("ВПКредит", default = 0, null=True, blank=True)
	VPOPFU                  = models.IntegerField("ВПОПФУ", default = 0, null=True, blank=True)
	VPProchieOPFU           = models.IntegerField("ВППрочиеОПФУ", default = 0, null=True, blank=True)
	VyruchkaZaAvto          = models.IntegerField("ВыручкаЗаАвто", default = 0, null=True, blank=True)
	VyruchkaZCH             = models.IntegerField("ВыручкаЗЧ", default = 0, null=True, blank=True)
	VyruchkaSHiny           = models.IntegerField("ВыручкаШины", default = 0, null=True, blank=True)
	God                     = models.IntegerField("Год", default = 0, null=True, blank=True)
	DataKontraktovaniya     = models.DateTimeField("ДатаКонтрактования", null=True, blank=True)
	DataPostupleniya        = models.DateTimeField("ДатаПоступления", null=True, blank=True)
	DataProdazhi            = models.DateTimeField("ДатаПродажи", null=True, blank=True)
	DataProdazhiTrejdIn     = models.DateTimeField("ДатаПродажиТрейдИн", null=True, blank=True)
	Den                     = models.IntegerField("День", default = 0, null=True, blank=True)
	DopyVCene               = models.IntegerField("ДопыВЦене", default = 0, null=True, blank=True)
	DopySebestoimost        = models.IntegerField("ДопыСебестоимость", default = 0, null=True, blank=True)
	IstochnikAM             = models.CharField("ИсточникАМ", max_length=150, null=True, blank=True)
	KategoriyaDniNaSklade   = models.CharField("КатегорияДниНаСкладе", max_length=150, null=True, blank=True)
	KVP                     = models.IntegerField("КВП", default = 0, null=True, blank=True)
	Klient                  = models.CharField("Клиент", max_length=150, null=True, blank=True)
	KolichestvoAvto         = models.IntegerField("КоличествоАвто", default = 0, null=True, blank=True)
	KolichestvoGAP          = models.IntegerField("КоличествоГАП", default = 0, null=True, blank=True)
	KolichestvoKASKO        = models.IntegerField("КоличествоКАСКО", default = 0, null=True, blank=True)
	KolichestvoKredit       = models.IntegerField("КоличествоКредит", default = 0, null=True, blank=True)
	KolichestvoNCH          = models.IntegerField("КоличествоНЧ", default = 0, null=True, blank=True)
	KolichestvoOSAGO        = models.IntegerField("КоличествоОСАГО", default = 0, null=True, blank=True)
	KolichestvoProdanoTrejdIn   = models.IntegerField("КоличествоПроданоТрейдИн", default = 0, null=True, blank=True)
	KolichestvoSZH          = models.IntegerField("КоличествоСЖ", default = 0, null=True, blank=True)
	KolichestvoTrejdIn      = models.IntegerField("КоличествоТрейдИн", default = 0, null=True, blank=True)
	KolichestvoSHiny        = models.IntegerField("КоличествоШины", default = 0, null=True, blank=True)
	KompensaciyaProchixSkidok   = models.IntegerField("КомпенсацияПрочихСкидок", default = 0, null=True, blank=True)
	KompensaciyaSkidokTrejdIn   = models.IntegerField("КомпенсацияСкидокТрейдИн", default = 0, null=True, blank=True)
	ListOcenkiVIN           = models.CharField("ЛистОценкиVIN", max_length=150, null=True, blank=True)
	MarzhaTrejdIn           = models.IntegerField("МаржаТрейдИн", default = 0, null=True, blank=True)
	Marka                   = models.CharField("Марка", max_length=150, null=True, blank=True)
	Mesyac                  = models.IntegerField("Месяц", default = 0, null=True, blank=True)
	Model                   = models.CharField("Модель", max_length=150, null=True, blank=True)
	Nedelya                 = models.IntegerField("Неделя", default = 0, null=True, blank=True)
	PodarkiSebestoimost     = models.IntegerField("ПодаркиСебестоимость", default = 0, null=True, blank=True)
	PodrazdelenieDC         = models.CharField("ПодразделениеДЦ", max_length=150, null=True, blank=True)
	Prodavec                = models.CharField("Продавец", max_length=150, null=True, blank=True)
	RRC                     = models.IntegerField("РРЦ", default = 0, null=True, blank=True)
	SebestoimostZCH         = models.IntegerField("СебестоимостьЗЧ", default = 0, null=True, blank=True)
	SebestoimostPoDokumentu = models.IntegerField("СебестоимостьПоДокументу", default = 0, null=True, blank=True)
	SebestoimostPodryad     = models.IntegerField("СебестоимостьПодряд", default = 0, null=True, blank=True)
	SebestoimostSHiny       = models.IntegerField("СебестоимостьШины", default = 0, null=True, blank=True)
	SkidkaDC                = models.IntegerField("СкидкаДЦ", default = 0, null=True, blank=True)
	SkidkaProchaya          = models.IntegerField("СкидкаПрочая", default = 0, null=True, blank=True)
	SkidkaTrejdIn           = models.IntegerField("СкидкаТрейдИн", default = 0, null=True, blank=True)
	SummaAktivnyeProdazhi   = models.IntegerField("СуммаАктивныеПродажи", default = 0, null=True, blank=True)
	SummaKASKO              = models.IntegerField("СуммаКАСКО", default = 0, null=True, blank=True)
	SummaKreditaGAP         = models.IntegerField("СуммаКредитаГАП", default = 0, null=True, blank=True)
	SummaMarzhiBezNDS       = models.IntegerField("СуммаМаржиБезНДС", default = 0, null=True, blank=True)
	SummaOSAGO              = models.IntegerField("СуммаОСАГО", default = 0, null=True, blank=True)
	SummaPodryad            = models.IntegerField("СуммаПодряд", default = 0, null=True, blank=True)
	SummaPriema             = models.IntegerField("СуммаПриема", default = 0, null=True, blank=True)
	SummaProdazhiKomplektov = models.IntegerField("СуммаПродажиКомплектов", default = 0, null=True, blank=True)
	SummaRabot              = models.IntegerField("СуммаРабот", default = 0, null=True, blank=True)
	SummaSertifikat         = models.IntegerField("СуммаСертификат", default = 0, null=True, blank=True)
	SummaSZH                = models.IntegerField("СуммаСЖ", default = 0, null=True, blank=True)
	SummaTrejdInPoPlanu     = models.IntegerField("СуммаТрейдИнПоПлану", default = 0, null=True, blank=True)
	TipProdazhi             = models.CharField("ТипПродажи", max_length=150, null=True, blank=True)
	Firma                   = models.CharField("Фирма", max_length=150, null=True, blank=True)
	KolichestvoProdanyxKomplektov   = models.IntegerField("КоличествоПроданыхКомплектов", default = 0, null=True, blank=True)
	KolichestvoProchieOPFU          = models.IntegerField("КоличествоПрочиеОПФУ", default = 0, null=True, blank=True)
	SummaKarty              = models.IntegerField("СуммаКарты", default = 0, null=True, blank=True)
	KolichestvoKarty        = models.IntegerField("КоличествоКарты", default = 0, null=True, blank=True)
	SummaGAP                = models.IntegerField("СуммаГАП", default = 0, null=True, blank=True)
	GodVypuska              = models.CharField("ГодВыпуска", max_length=150, null=True, blank=True)

	def __str__(self):
		return "{} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} ".format( self.OurCompany, self.SoglashenieNomer, self.SoglashenieData, self.FilialPriema, self.RRCPervonachalnaya, self.ListOcenkiKlientVidKontragenta, self.ListOcenkiKlient, self.SummaEkvajring, self.FaktAdres, self.VIN, self.Adres, self.VidKontragenta, self.VPDopy, self.VPKredit, self.VPOPFU, self.VPProchieOPFU, self.VyruchkaZaAvto, self.VyruchkaZCH, self.VyruchkaSHiny, self.God, self.DataKontraktovaniya, self.DataPostupleniya, self.DataProdazhi, self.DataProdazhiTrejdIn, self.Den, self.DopyVCene, self.DopySebestoimost, self.IstochnikAM, self.KategoriyaDniNaSklade, self.KVP, self.Klient, self.KolichestvoAvto, self.KolichestvoGAP, self.KolichestvoKASKO, self.KolichestvoKredit, self.KolichestvoNCH, self.KolichestvoOSAGO, self.KolichestvoProdanoTrejdIn, self.KolichestvoSZH, self.KolichestvoTrejdIn, self.KolichestvoSHiny, self.KompensaciyaProchixSkidok, self.KompensaciyaSkidokTrejdIn, self.ListOcenkiVIN, self.MarzhaTrejdIn, self.Marka, self.Mesyac, self.Model, self.Nedelya, self.PodarkiSebestoimost, self.PodrazdelenieDC, self.Prodavec, self.RRC, self.SebestoimostZCH, self.SebestoimostPoDokumentu, self.SebestoimostPodryad, self.SebestoimostSHiny, self.SkidkaDC, self.SkidkaProchaya, self.SkidkaTrejdIn, self.SummaAktivnyeProdazhi, self.SummaKASKO, self.SummaKreditaGAP, self.SummaMarzhiBezNDS, self.SummaOSAGO, self.SummaPodryad, self.SummaPriema, self.SummaProdazhiKomplektov, self.SummaRabot, self.SummaSertifikat, self.SummaSZH, self.SummaTrejdInPoPlanu, self.TipProdazhi, self.Firma, self.KolichestvoProdanyxKomplektov, self.KolichestvoProchieOPFU, self.SummaKarty, self.KolichestvoKarty, self.SummaGAP, self.GodVypuska,)  

	class Meta:
		db_table = 'CumulativeMarginUS'
		verbose_name = 'ПлоскаяТаблицаКумулятивнаяМаржаБУ'
		verbose_name_plural = 'ПлоскаяТаблицаКумулятивнаяМаржаБУ'


class CumulativeMargin(models.Model):
	SummaEkvajring          = models.IntegerField("СуммаЭквайринг", default = 0, null=True, blank=True)
	FaktAdres               = models.CharField("ФактАдрес", max_length=150, null=True, blank=True)
	Firma                   = models.CharField("Фирма", max_length=150, null=True, blank=True)
	SummaKreditaGAP         = models.IntegerField("СуммаКредитаГАП", default = 0, null=True, blank=True)
	KolichestvoGAP          = models.IntegerField("КоличествоГАП", default = 0, null=True, blank=True)
	SummaOSAGO              = models.IntegerField("СуммаОСАГО", default = 0, null=True, blank=True)
	KolichestvoOSAGO        = models.IntegerField("КоличествоОСАГО", default = 0, null=True, blank=True)
	SummaGAP                = models.IntegerField("СуммаГАП", default = 0, null=True, blank=True)
	OplataPoKASKO           = models.IntegerField("ОплатаПоКАСКО", default = 0, null=True, blank=True)
	OplataPoOSAGO           = models.IntegerField("ОплатаПоОСАГО", default = 0, null=True, blank=True)
	SummaPriema             = models.IntegerField("СуммаПриема", default = 0, null=True, blank=True)
	SummaGosReg             = models.IntegerField("СуммаГосрег", default = 0, null=True, blank=True)
	GosregIS                = models.IntegerField("ЕстьГосрегистрация", default = 0, null=True, blank=True)
	DataVykupa              = models.DateTimeField("ДатаВыкупа", null=True, blank=True)
	DataOtchitana           = models.DateTimeField("ДатаОтчитана", null=True, blank=True)
	SummaKarty              = models.IntegerField("СуммаКарты", default = 0, null=True, blank=True)
	KolichestvoKarty        = models.IntegerField("КоличествоКарты", default = 0, null=True, blank=True)
	SummaKompensaciiBezNDS  = models.IntegerField("СуммаКомпенсацииБезНДС", default = 0, null=True, blank=True)
	KolichestvoProchieOPFU  = models.IntegerField("КоличествоПрочиеОПФУ", default = 0, null=True, blank=True)
	SummaPoPrezidentu       = models.IntegerField("СуммаПоПрезиденту", default = 0, null=True, blank=True)
	VidProdazhi             = models.CharField("ВидПродажи", max_length=150, null=True, blank=True)
	VIN                     = models.CharField("VIN", max_length=150, null=True, blank=True)
	Adres                   = models.CharField("Адрес", max_length=150, null=True, blank=True)
	GrossProfitSP           = models.IntegerField("ВаловаяПрибыльЗЧ", default = 0, null=True, blank=True)
	GrossProfitTire         = models.IntegerField("ВаловаяПрибыльЗЧШины", default = 0, null=True, blank=True)
	PartnerType             = models.CharField("ВидКонтрагента", max_length=150, null=True, blank=True)
	GrossProfitAdds         = models.IntegerField("ВПДопы", default = 0, null=True, blank=True)
	GrossProfitCredit       = models.IntegerField("ВПКредит", default = 0, null=True, blank=True)
	GrossProfitSDFS         = models.IntegerField("ВПОПФУ", default = 0, null=True, blank=True)
	GrossProfitSDFSOther    = models.IntegerField("ВППрочиеОПФУ", default = 0, null=True, blank=True)
	ProceedsCar             = models.IntegerField("ВыручкаЗаАвто", default = 0, null=True, blank=True)
	ProceedsSP              = models.IntegerField("ВыручкаЗЧ", default = 0, null=True, blank=True)
	ProceedsTire            = models.IntegerField("ВыручкаШины", default = 0, null=True, blank=True)
	Year                    = models.IntegerField("Год", default = 0, null=True, blank=True)
	ContractDate            = models.DateTimeField("ДатаКонтрактования", null=True, blank=True)
	ReceiptDate             = models.DateTimeField("ДатаПоступления", null=True, blank=True)
	SaleDate                = models.DateTimeField("ДатаПродажи", null=True, blank=True)
	SaleDateTraidIn         = models.DateTimeField("ДатаПродажиТрейдИн", null=True, blank=True)
	Day                     = models.IntegerField("День", default = 0, null=True, blank=True)
	AddsInPrice             = models.IntegerField("ДопыВЦене", default = 0, null=True, blank=True)
	AddsInCostPrice         = models.IntegerField("ДопыСебестоимость", default = 0, null=True, blank=True)
	DaysOfStorage           = models.CharField("КатегорияДниНаСкладе", max_length=150, null=True, blank=True)
	Cum                     = models.IntegerField("КВП", default = 0, null=True, blank=True)
	Client                  = models.CharField("Клиент", max_length=150, null=True, blank=True)
	AmountOfCars            = models.IntegerField("КоличествоАвто", default = 0, null=True, blank=True)
	AmountOfKASKO           = models.IntegerField("КоличествоКАСКО", default = 0, null=True, blank=True)
	AmountOfCredit          = models.IntegerField("КоличествоКредит", default = 0, null=True, blank=True)
	AmountOfNH              = models.IntegerField("КоличествоНЧ", default = 0, null=True, blank=True)
	AmountOfSaleTraidInCars = models.IntegerField("КоличествоПроданоТрейдИн", default = 0, null=True, blank=True)
	AmountOfLI              = models.IntegerField("КоличествоСЖ", default = 0, null=True, blank=True)
	AmountOfTraidInCars     = models.IntegerField("КоличествоТрейдИн", default = 0, null=True, blank=True)
	AmountOfTires           = models.IntegerField("КоличествоШины", default = 0, null=True, blank=True)
	CompensationOtherDiscount       = models.IntegerField("КомпенсацияПрочихСкидок", default = 0, null=True, blank=True)
	CompensationTrainInDiscount     = models.IntegerField("КомпенсацияСкидокТрейдИн", default = 0, null=True, blank=True)
	VINTraidIn              = models.CharField("ЛистОценкиVIN", max_length=150, null=True, blank=True)
	MarginTraidIn           = models.IntegerField("МаржаТрейдИн", default = 0, null=True, blank=True)
	Mark                    = models.CharField("Марка", max_length=150, null=True, blank=True)
	Month                   = models.IntegerField("Месяц", default = 0, null=True, blank=True)
	MonthDate               = models.DateTimeField("МесяцПродажи", null=True, blank=True)
	Model                   = models.CharField("Модель", max_length=150, null=True, blank=True)
	Week                    = models.IntegerField("Неделя", default = 0, null=True, blank=True)
	PresentsCostPrice       = models.IntegerField("ПодаркиСебестоимость", default = 0, null=True, blank=True)
	CFO                     = models.CharField("ПодразделениеДЦ", max_length=150, null=True, blank=True)
	Manager                 = models.CharField("Продавец", max_length=150, null=True, blank=True)
	RRP                     = models.IntegerField("РРЦ", default = 0, null=True, blank=True)
	SameRegion              = models.CharField("СвойРегион", max_length=150, null=True, blank=True)
	SPCostPrice             = models.IntegerField("СебестоимостьЗЧ", default = 0, null=True, blank=True)
	CarCostPrice            = models.IntegerField("СебестоимостьПоДокументу", default = 0, null=True, blank=True)
	ContractWorksCostPrice  = models.IntegerField("СебестоимостьПодряд", default = 0, null=True, blank=True)
	TireCostPrice           = models.IntegerField("СебестоимостьШины", default = 0, null=True, blank=True)
	DiscountCFO             = models.IntegerField("СкидкаДЦ", default = 0, null=True, blank=True)
	DiscountOther           = models.IntegerField("СкидкаПрочая", default = 0, null=True, blank=True)
	DiscountTraidIn         = models.IntegerField("СкидкаТрейдИн", default = 0, null=True, blank=True)
	AddSales                = models.IntegerField("СуммаАктивныеПродажи", default = 0, null=True, blank=True)
	ProseedsKASKO           = models.IntegerField("СуммаКАСКО", default = 0, null=True, blank=True)
	Margin                  = models.IntegerField("СуммаМаржиБезНДС", default = 0, null=True, blank=True)
	ContractWorksProceeds   = models.IntegerField("СуммаПодряд", default = 0, null=True, blank=True)
	WorksProceeds           = models.IntegerField("СуммаРабот", default = 0, null=True, blank=True)
	SertificatProceeds      = models.IntegerField("СуммаСертификат", default = 0, null=True, blank=True)
	LIProceeds              = models.IntegerField("СуммаСЖ", default = 0, null=True, blank=True)
	PlanMarginTraidIn       = models.IntegerField("СуммаТрейдИнПоПлану", default = 0, null=True, blank=True)
	TypeOfSale              = models.CharField("ТипПродажи", max_length=150, null=True, blank=True)

	def __str__(self):
		return "{} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} ".format( self.SummaEkvajring, self.FaktAdres, self.Firma, self.SummaKreditaGAP, self.KolichestvoGAP, self.SummaOSAGO, self.KolichestvoOSAGO, self.SummaGAP, self.OplataPoKASKO, self.OplataPoOSAGO, self.SummaPriema, self.SummaGosReg, self.GosregIS, self.DataVykupa, self.DataOtchitana, self.SummaKarty, self.KolichestvoKarty, self.SummaKompensaciiBezNDS, self.KolichestvoProchieOPFU, self.SummaPoPrezidentu, self.VidProdazhi, self.VIN, self.Adres, self.GrossProfitSP, self.GrossProfitTire, self.PartnerType, self.GrossProfitAdds, self.GrossProfitCredit, self.GrossProfitSDFS, self.GrossProfitSDFSOther, self.ProceedsCar, self.ProceedsSP, self.ProceedsTire, self.Year, self.ContractDate, self.ReceiptDate, self.SaleDate, self.SaleDateTraidIn, self.Day, self.AddsInPrice, self.AddsInCostPrice, self.DaysOfStorage, self.Cum, self.Client, self.AmountOfCars, self.AmountOfKASKO, self.AmountOfCredit, self.AmountOfNH, self.AmountOfSaleTraidInCars, self.AmountOfLI, self.AmountOfTraidInCars, self.AmountOfTires, self.CompensationOtherDiscount, self.CompensationTrainInDiscount, self.VINTraidIn, self.MarginTraidIn, self.Mark, self.Month, self.MonthDate, self.Model, self.Week, self.PresentsCostPrice, self.CFO, self.Manager, self.RRP, self.SameRegion, self.SPCostPrice, self.CarCostPrice, self.ContractWorksCostPrice, self.TireCostPrice, self.DiscountCFO, self.DiscountOther, self.DiscountTraidIn, self.AddSales, self.ProseedsKASKO, self.Margin, self.ContractWorksProceeds, self.WorksProceeds, self.SertificatProceeds, self.LIProceeds, self.PlanMarginTraidIn, self.TypeOfSale,)  

	class Meta:
		db_table = 'CumulativeMargin'
		verbose_name = 'ПлоскаяТаблицаКумулятивнаяМаржа'
		verbose_name_plural = 'ПлоскаяТаблицаКумулятивнаяМаржа'


class ComparativeReportOPFU(models.Model):
	VIN             = models.CharField("VIN", max_length=150, null=True, blank=True)
	VidKASKO        = models.CharField("ВидКАСКО", max_length=150, null=True, blank=True)
	VidKlienta      = models.CharField("ВидКлиента", max_length=150, null=True, blank=True)
	VidStraxovaniya = models.CharField("ВидСтрахования", max_length=150, null=True, blank=True)
	Gorod           = models.CharField("Город", max_length=150, null=True, blank=True)
	DataNachalaPolisa       = models.DateTimeField("ДатаНачалаПолиса", null=True, blank=True)
	DataOkonchaniyaPolisa   = models.DateTimeField("ДатаОкончанияПолиса", null=True, blank=True)
	DataPlatezha            = models.DateTimeField("ДатаПлатежа", null=True, blank=True)
	DolzhnostProdavca       = models.CharField("ДолжностьПродавца", max_length=150, null=True, blank=True)
	Klient                  = models.CharField("Клиент", max_length=150, null=True, blank=True)
	Kolichestvo             = models.IntegerField("Количество", default = 0, null=True, blank=True)
	KomissiyaBezNDS         = models.IntegerField("КомиссияБезНДС", default = 0, null=True, blank=True)
	KomissiyaSNDS           = models.IntegerField("КомиссияСНДС", default = 0, null=True, blank=True)
	Kreditnyj               = models.CharField("Кредитный", max_length=150, null=True, blank=True)
	Marka                   = models.CharField("Марка", max_length=150, null=True, blank=True)
	Model                   = models.CharField("Модель", max_length=150, null=True, blank=True)
	NovyjProlongaciya       = models.CharField("НовыйПролонгация", max_length=150, null=True, blank=True)
	Nomer                   = models.CharField("Номер", max_length=150, null=True, blank=True)
	OplachenayaPremiya      = models.IntegerField("ОплаченаяПремия", default = 0, null=True, blank=True)
	Otgruzheno              = models.DateTimeField("Отгружено", null=True, blank=True)
	PodrazdelenieDCVnutr    = models.CharField("ПодразделениеДЦВнутр", max_length=150, null=True, blank=True)
	Procent                 = models.IntegerField("Процент", default = 0, null=True, blank=True)
	SoglashenieNomer        = models.CharField("СоглашениеНомер", max_length=150, null=True, blank=True)
	StraxovayaKompaniyaBank = models.CharField("СтраховаяКомпанияБанк", max_length=150, null=True, blank=True)
	StraxovayaPremiya       = models.IntegerField("СтраховаяПремия", default = 0, null=True, blank=True)
	StraxovayaSummaSNDS     = models.IntegerField("СтраховаяСуммаСНДС", default = 0, null=True, blank=True)
	FIOOPFU                 = models.CharField("ФИООПФУ", max_length=150, null=True, blank=True)
	FIOProdavca             = models.CharField("ФИОПродавца", max_length=150, null=True, blank=True)
	Firma                   = models.CharField("Фирма", max_length=150, null=True, blank=True)
	VINNov                  = models.CharField("VINНов", max_length=150, null=True, blank=True)
	Period                  = models.DateTimeField("Период", null=True, blank=True)
	PodrazdelenieDCNov      = models.CharField("ПодразделениеДЦНов", max_length=150, null=True, blank=True)
	KlientNov               = models.CharField("КлиентНов", max_length=150, null=True, blank=True)

	def __str__(self):
		return "{} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} ".format( self.VIN, self.VidKASKO, self.VidKlienta, self.VidStraxovaniya, self.Gorod, self.DataNachalaPolisa, self.DataOkonchaniyaPolisa, self.DataPlatezha, self.DolzhnostProdavca, self.Klient, self.Kolichestvo, self.KomissiyaBezNDS, self.KomissiyaSNDS, self.Kreditnyj, self.Marka, self.Model, self.NovyjProlongaciya, self.Nomer, self.OplachenayaPremiya, self.Otgruzheno, self.PodrazdelenieDCVnutr, self.Procent, self.SoglashenieNomer, self.StraxovayaKompaniyaBank, self.StraxovayaPremiya, self.StraxovayaSummaSNDS, self.FIOOPFU, self.FIOProdavca, self.Firma, self.VINNov, self.Period, self.PodrazdelenieDCNov, self.KlientNov,)  

	class Meta:
		db_table = 'ComparativeReportOPFU'
		verbose_name = 'СравнительныйОтчетОПФУ'
		verbose_name_plural = 'СравнительныйОтчетОПФУ'


class Stock(models.Model):
	NotForSale = models.CharField("НеДляПродажи", max_length=512, null=True, blank=True)
	IdKomplectation = models.CharField("ИДКомплектация", max_length=512, null=True, blank=True)
	IdModification 	= models.CharField("ИДМодификация", max_length=512, null=True, blank=True)
	VIN = models.CharField("VIN", max_length=512, null=True, blank=True)
	VidKontragenta = models.CharField("ВидКонтрагента", max_length=512, null=True, blank=True)
	VxodnayaStoimost = models.IntegerField("ВходнаяСтоимость", default = 0, null=True, blank=True)
	Vyruchka = models.IntegerField("Выручка", default = 0, null=True, blank=True)
	DataKontrakta = models.DateTimeField("ДатаКонтракта", null=True, blank=True)
	DataOkonchaniyaKonsignacii = models.DateTimeField("ДатаОкончанияКонсигнации", null=True, blank=True)
	DataOplaty = models.DateTimeField("ДатаОплаты", null=True, blank=True)
	DataOtcheta = models.DateTimeField("ДатаОтчета", null=True, blank=True)
	DataOtchitana = models.DateTimeField("ДатаОтчитана", null=True, blank=True)
	DataPostupleniyaNaSklad = models.DateTimeField("ДатаПоступленияНаСклад", null=True, blank=True)
	DataStopOtgruzka = models.DateTimeField("ДатаСтопОтгрузка", null=True, blank=True)
	Obem = models.IntegerField("Объем", default = 0, null=True, blank=True)
	Dostupnost = models.CharField("Доступность", max_length=512, null=True, blank=True)
	ZalogSumma = models.IntegerField("ЗалогСумма", default = 0, null=True, blank=True)
	Klient = models.CharField("Клиент", max_length=512, null=True, blank=True)
	Kolichestvo = models.IntegerField("Количество", default = 0, null=True, blank=True)
	Komplektaciya = models.CharField("Комплектация", max_length=512, null=True, blank=True)
	Marka = models.CharField("Марка", max_length=512, null=True, blank=True)
	Menedzher = models.CharField("Менеджер", max_length=512, null=True, blank=True)
	Model = models.CharField("Модель", max_length=512, null=True, blank=True)
	Moshhnost_LS = models.IntegerField("Мощность_ЛС", default = 0, null=True, blank=True)
	PlaniruemayaDataVydachi = models.DateTimeField("ПланируемаяДатаВыдачи", null=True, blank=True)
	PlanovayaDataOplaty = models.DateTimeField("ПлановаяДатаОплаты", null=True, blank=True)
	PlanovayaCenaRealizacii = models.IntegerField("ПлановаяЦенаРеализации", default = 0, null=True, blank=True)
	PoNalichiyu = models.CharField("ПоНаличию", max_length=512, null=True, blank=True)
	PodrazdelenieDC = models.CharField("ПодразделениеДЦ", max_length=512, null=True, blank=True)
	StatusAM = models.CharField("СтатусАМ", max_length=512, null=True, blank=True)
	Finansirovanie = models.CharField("Финансирование", max_length=512, null=True, blank=True)
	Firma = models.CharField("Фирма", max_length=512, null=True, blank=True)
	Cvet = models.CharField("Цвет", max_length=512, null=True, blank=True)
	RRC = models.IntegerField("РРЦ", default = 0, null=True, blank=True)
	GodVypuska = models.CharField("ГодВыпуска", max_length=512, null=True, blank=True)
	Postavshik = models.CharField("Поставщик", max_length=512, null=True, blank=True)
	Postuplenie = models.CharField("Поступление", max_length=512, null=True, blank=True)
	SummaTrejdIn = models.IntegerField("СуммаТрейдИн", default = 0, null=True, blank=True)
	Alfa = models.CharField("Альфа", max_length=512, null=True, blank=True)
	DataPostanovkiNaUchet = models.DateTimeField("ДатаПостановкиНаУчет", null=True, blank=True)
	GosNomer = models.CharField("ГосНомер", max_length=512, null=True, blank=True)
	DataSnyatiyaSUcheta = models.DateTimeField("ДатаСнятияСУчета", null=True, blank=True)
	SvedORegTS = models.CharField("СведОРегТС", max_length=512, null=True, blank=True)
	NomerSoglasheniya = models.CharField("НомерСоглашения", max_length=512, null=True, blank=True)
	KodKomplektacii = models.CharField("КодКомплектации", max_length=512, null=True, blank=True)
	StoimostPrixod = models.IntegerField("СтоимостьПриход", default = 0, null=True, blank=True)
	RaznicaStoimosti = models.IntegerField("РазницаСтоимости", default = 0, null=True, blank=True)
	DataOplatyZakazPostavshhiku = models.DateTimeField("ДатаОплатыЗаказПоставщику", null=True, blank=True)
	OplataDengami = models.IntegerField("ОплатаДеньгами", default = 0, null=True, blank=True)
	OplataVzaimozachet = models.IntegerField("ОплатаВзаимозачет", default = 0, null=True, blank=True)
	City = models.CharField("ПодразделениеДЦ", max_length=512, null=True, blank=True)
	
	def __str__(self):
		return "{} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} ".format( self.NotForSale, self.IdKomplectation, self.VIN, self.VidKontragenta, self.VxodnayaStoimost, self.Vyruchka, self.DataKontrakta, self.DataOkonchaniyaKonsignacii, self.DataOplaty, self.DataOtcheta, self.DataOtchitana, self.DataPostupleniyaNaSklad, self.DataStopOtgruzka, self.Obem, self.Dostupnost, self.ZalogSumma, self.Klient, self.Kolichestvo, self.Komplektaciya, self.Marka, self.Menedzher, self.Model, self.Moshhnost_LS, self.PlaniruemayaDataVydachi, self.PlanovayaDataOplaty, self.PlanovayaCenaRealizacii, self.PoNalichiyu, self.PodrazdelenieDC, self.StatusAM, self.Finansirovanie, self.Firma, self.Cvet, self.RRC, self.GodVypuska, self.Postavshik, self.Postuplenie, self.SummaTrejdIn, self.Alfa, self.DataPostanovkiNaUchet, self.GosNomer, self.DataSnyatiyaSUcheta, self.SvedORegTS, self.NomerSoglasheniya, self.KodKomplektacii, self.StoimostPrixod, self.RaznicaStoimosti, self.DataOplatyZakazPostavshhiku, self.OplataDengami, self.OplataVzaimozachet,)  

	class Meta:
		db_table = 'Stock'
		verbose_name = 'СтокДЦПлоскаяПоДням'
		verbose_name_plural = 'СтокДЦПлоскаяПоДням'