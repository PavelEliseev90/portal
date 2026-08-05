-- =============================================================================
-- MSSQL: таблица TradeInFunnel под колонки выгрузки
-- Источник: /eco/funnel/simple-export/
-- Загрузка с портала: кнопка «Загрузить в MSSQL»
--   1) DELETE WHERE EstimationDate BETWEEN @start AND @end (+ фильтры Unit*)
--   2) INSERT строк
-- =============================================================================

IF OBJECT_ID(N'dbo.TradeInFunnel', N'U') IS NOT NULL
BEGIN
    DROP TABLE dbo.TradeInFunnel;
END
GO

CREATE TABLE dbo.TradeInFunnel
(
    Id                      BIGINT IDENTITY(1,1) NOT NULL,
    LoadedAt                DATETIME2(0)         NOT NULL
        CONSTRAINT DF_TradeInFunnel_LoadedAt DEFAULT (SYSUTCDATETIME()),

    EstimationDate          DATETIME2(0)     NULL,  -- Дата (date_start_estimation)
    UnitName                NVARCHAR(255)    NULL,  -- ДЦ оценки
    UnitSourceName          NVARCHAR(255)    NULL,  -- Подразделение источник
    TypeReceptionName       NVARCHAR(255)    NULL,  -- Тип оценки
    MarkName                NVARCHAR(255)    NULL,  -- Марка
    ModelName               NVARCHAR(255)    NULL,  -- Модель
    RunKm                   INT              NULL,  -- Пробег
    [Year]                  INT              NULL,  -- Год
    Vin                     NVARCHAR(64)     NULL,  -- VIN
    RlkNumber               NVARCHAR(255)    NULL,  -- Номер РЛ оценки
    RlkDate                 DATETIME2(0)     NULL,  -- Дата РЛ оценки
    SourceOpRlkNumber       NVARCHAR(255)    NULL,  -- Номер РЛ ОП (источник / footing)
    SourceOpRlkDate         DATETIME2(0)     NULL,  -- Дата РЛ ОП (источник / footing)
    Accepted                NVARCHAR(10)     NULL,  -- Принят (Да/Нет)
    Stage                   NVARCHAR(255)    NULL,  -- Статус оценки
    CostPreparation         DECIMAL(18, 2)   NULL,  -- Затраты на подготовку
    CostMcu                 DECIMAL(18, 2)   NULL,  -- Затраты кузовной участок
    CostSs                  DECIMAL(18, 2)   NULL,  -- Затраты слесарный участок
    PriceBeforeKd           DECIMAL(18, 2)   NULL,  -- Цена до КД
    PriceAfterKd            DECIMAL(18, 2)   NULL,  -- Цена после КД
    MarketPriceRub          DECIMAL(18, 2)   NULL,  -- Рынок руб.

    CONSTRAINT PK_TradeInFunnel PRIMARY KEY CLUSTERED (Id)
);
GO

CREATE NONCLUSTERED INDEX IX_TradeInFunnel_EstimationDate
    ON dbo.TradeInFunnel (EstimationDate);
GO

CREATE NONCLUSTERED INDEX IX_TradeInFunnel_Vin
    ON dbo.TradeInFunnel (Vin)
    WHERE Vin IS NOT NULL AND Vin <> N'';
GO

CREATE NONCLUSTERED INDEX IX_TradeInFunnel_Unit_EstimationDate
    ON dbo.TradeInFunnel (UnitName, EstimationDate);
GO

-- Для уже существующей таблицы без колонок РЛ ОП выполните:
--   scripts/mssql_alter_tradeinfunnel_source_op_rlk.sql
