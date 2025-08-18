from django.contrib import admin
from powerbi.models import mers_SQL, Bi_logs, StockTZK, MKU_State_Orders, EstimationOP, CumulativeMarginUS, CumulativeMargin, ComparativeReportOPFU, Bi_wash


@admin.register(Bi_wash)
class Bi_washAdmin(admin.ModelAdmin):
	list_display 	= ('date_time', 'card_number', 'wash_id', 'source_type', 'source_number', 'dest_type', 'dest_number', 'subject', 'payment_type', 'amount', ) 
	list_filter	 	= ('subject', 'payment_type',)
	search_fields 	= ('card_number',)


@admin.register(Bi_logs)
class Bi_logsAdmin(admin.ModelAdmin):
	list_display = ('date', 'bi_model', 'count_add', 'count_delite', 'filtr', ) 


@admin.register(mers_SQL)
class mers_SQLAdmin(admin.ModelAdmin):
	list_display = ('VIN', 'Administrator', 'AdministratorDolznost', 'VidZakazNaryda', 'VyruchkaPoZapchastyam', 'GodVypuska', 'GruppaPDC', 'DataOtcrytiyaZN', 'Klient', 'KolichestvoNCHPodryad', 'Marka', 'MasterPriemshhik', 'MasterPriemshhikDolzhnost', 'Mashinozaezdy', 'Mexanik', 'MexanikDolzhnost', 'Model', 'Nomenclatura', 'Artikul', 'NomerZakazNaryada', 'Normochasy', 'Period', 'Sebestoimost', 'SummaSubpodryad', 'PodrazdelenieDC', 'Stoimost', 'VidKontragent',)


@admin.register(StockTZK)
class StockTZKAdmin(admin.ModelAdmin):
	list_display = ('VidOprosa', 'NPS', 'TZK', 'SpeedService', 'Personal', 'feedback', 'Cuality', 'Q7', 'BL', 'Cancel', 'Negative', 'Qwest', 'IsService', 'Pokupka', 'Vidacha', 'TradeIN', 'VIN', 'VsegoKlientovObsluzheno', 'OproshenoKlientov', 'ZakrytOpros', 'Promouter', 'Nejtral', 'NejtralyCHS', 'NejtralOtkazOtOprosa', 'Kritiki', 'PrinuditelnoeZakrytie', 'DovolnyeNegativaNet', 'NedovolnyeKlienty', 'DolgijRemont', 'DorogoeObsluzhivanie', 'KachestvoRemonta', 'nekorrRabotaPriemki', 'OtsutstvieZCH', 'OtkazVGarantii', 'Prochee', 'NegativNeSnyat', 'OprosNeProveden', 'OprosObrabotan', 'TelefonNeOtvechaet', 'NN_Nedovolki', 'VRabote', 'VidKlienta', 'ZNNomer', 'ZNData', 'PodrazdelenieDC', 'DataOprosa', 'NomerOprosa',)


@admin.register(MKU_State_Orders)
class MKU_State_OrdersAdmin(admin.ModelAdmin):
	list_display = ('Period', 'MZ_State', 'ZN_Number', 'ZN_Date', 'MZ_Number', 'MZ_Date', 'responisble_Person', 'Insurance_Referral', 'Brand_Model', 'GosNumber', 'Owner', 'VIN', 'Repair_Type', 'Parts_Ordered', 'Parts_Arriving_Date_Fact', 'ZN_Status', 'Normochasy', 'Revenue_Works', 'Revenue_Parts', 'Cost_LKM', 'Revenue_LKM', 'Sum_Paid', 'Payer_Name', 'Payer_Group', 'Last_Comment', 'PodrazdelenieDC', 'Last_Comment_Date', 'GRAFIK_Date', 'VYDACHA_Date', 'Osmotr', 'Next_Month',)


@admin.register(EstimationOP)
class EstimationOPAdmin(admin.ModelAdmin):
	list_display = ('OprosData', 'Akcii', 'VesVoprosa', 'Vizity', 'Vsego', 'GruppaPDC', 'DSK', 'EstKontaktnayaInformaciya', 'ZvonokBezOtveta', 'Logika', 'Menedzher', 'NePodlezhitOcenke', 'Opros', 'Oceneno', 'OcenkaOtveta', 'PervichnyjZvonok', 'Perezvonili', 'PodrazdelenieDC', 'Poryadok', 'Potrebnosti', 'RabochijListData', 'RabochijListNomer', 'SozdanRL', 'Cena',)


@admin.register(CumulativeMarginUS)
class CumulativeMarginUSAdmin(admin.ModelAdmin):
	list_display = ('OurCompany', 'SoglashenieNomer', 'SoglashenieData', 'FilialPriema', 'RRCPervonachalnaya', 'ListOcenkiKlientVidKontragenta', 'ListOcenkiKlient', 'SummaEkvajring', 'FaktAdres', 'VIN', 'Adres', 'VidKontragenta', 'VPDopy', 'VPKredit', 'VPOPFU', 'VPProchieOPFU', 'VyruchkaZaAvto', 'VyruchkaZCH', 'VyruchkaSHiny', 'God', 'DataKontraktovaniya', 'DataPostupleniya', 'DataProdazhi', 'DataProdazhiTrejdIn', 'Den', 'DopyVCene', 'DopySebestoimost', 'IstochnikAM', 'KategoriyaDniNaSklade', 'KVP', 'Klient', 'KolichestvoAvto', 'KolichestvoGAP', 'KolichestvoKASKO', 'KolichestvoKredit', 'KolichestvoNCH', 'KolichestvoOSAGO', 'KolichestvoProdanoTrejdIn', 'KolichestvoSZH', 'KolichestvoTrejdIn', 'KolichestvoSHiny', 'KompensaciyaProchixSkidok', 'KompensaciyaSkidokTrejdIn', 'ListOcenkiVIN', 'MarzhaTrejdIn', 'Marka', 'Mesyac', 'Model', 'Nedelya', 'PodarkiSebestoimost', 'PodrazdelenieDC', 'Prodavec', 'RRC', 'SebestoimostZCH', 'SebestoimostPoDokumentu', 'SebestoimostPodryad', 'SebestoimostSHiny', 'SkidkaDC', 'SkidkaProchaya', 'SkidkaTrejdIn', 'SummaAktivnyeProdazhi', 'SummaKASKO', 'SummaKreditaGAP', 'SummaMarzhiBezNDS', 'SummaOSAGO', 'SummaPodryad', 'SummaPriema', 'SummaProdazhiKomplektov', 'SummaRabot', 'SummaSertifikat', 'SummaSZH', 'SummaTrejdInPoPlanu', 'TipProdazhi', 'Firma', 'KolichestvoProdanyxKomplektov', 'KolichestvoProchieOPFU', 'SummaKarty', 'KolichestvoKarty', 'SummaGAP', 'GodVypuska',)


@admin.register(CumulativeMargin)
class CumulativeMarginAdmin(admin.ModelAdmin):
	list_display = ('SummaEkvajring', 'FaktAdres', 'Firma', 'SummaKreditaGAP', 'KolichestvoGAP', 'SummaOSAGO', 'KolichestvoOSAGO', 'SummaGAP', 'OplataPoKASKO', 'OplataPoOSAGO', 'SummaPriema', 'SummaGosReg', 'GosregIS', 'DataVykupa', 'DataOtchitana', 'SummaKarty', 'KolichestvoKarty', 'SummaKompensaciiBezNDS', 'KolichestvoProchieOPFU', 'SummaPoPrezidentu', 'VidProdazhi', 'VIN', 'Adres', 'GrossProfitSP', 'GrossProfitTire', 'PartnerType', 'GrossProfitAdds', 'GrossProfitCredit', 'GrossProfitSDFS', 'GrossProfitSDFSOther', 'ProceedsCar', 'ProceedsSP', 'ProceedsTire', 'Year', 'ContractDate', 'ReceiptDate', 'SaleDate', 'SaleDateTraidIn', 'Day', 'AddsInPrice', 'AddsInCostPrice', 'DaysOfStorage', 'Cum', 'Client', 'AmountOfCars', 'AmountOfKASKO', 'AmountOfCredit', 'AmountOfNH', 'AmountOfSaleTraidInCars', 'AmountOfLI', 'AmountOfTraidInCars', 'AmountOfTires', 'CompensationOtherDiscount', 'CompensationTrainInDiscount', 'VINTraidIn', 'MarginTraidIn', 'Mark', 'Month', 'MonthDate', 'Model', 'Week', 'PresentsCostPrice', 'CFO', 'Manager', 'RRP', 'SameRegion', 'SPCostPrice', 'CarCostPrice', 'ContractWorksCostPrice', 'TireCostPrice', 'DiscountCFO', 'DiscountOther', 'DiscountTraidIn', 'AddSales', 'ProseedsKASKO', 'Margin', 'ContractWorksProceeds', 'WorksProceeds', 'SertificatProceeds', 'LIProceeds', 'PlanMarginTraidIn', 'TypeOfSale',)


@admin.register(ComparativeReportOPFU)
class ComparativeReportOPFUAdmin(admin.ModelAdmin):
	list_display = ('VIN', 'VidKASKO', 'VidKlienta', 'VidStraxovaniya', 'Gorod', 'DataNachalaPolisa', 'DataOkonchaniyaPolisa', 'DataPlatezha', 'DolzhnostProdavca', 'Klient', 'Kolichestvo', 'KomissiyaBezNDS', 'KomissiyaSNDS', 'Kreditnyj', 'Marka', 'Model', 'NovyjProlongaciya', 'Nomer', 'OplachenayaPremiya', 'Otgruzheno', 'PodrazdelenieDCVnutr', 'Procent', 'SoglashenieNomer', 'StraxovayaKompaniyaBank', 'StraxovayaPremiya', 'StraxovayaSummaSNDS', 'FIOOPFU', 'FIOProdavca', 'Firma', 'VINNov', 'Period', 'PodrazdelenieDCNov', 'KlientNov',)