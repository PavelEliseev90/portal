-- =============================================================================
-- MSSQL: добавить недостающие столбцы РЛ ОП в dbo.TradeInFunnel
-- Источник выгрузки: /eco/funnel/simple-export/
-- Безопасно для повторного запуска (колонки создаются только если их нет).
-- =============================================================================

SET NOCOUNT ON;

IF OBJECT_ID(N'dbo.TradeInFunnel', N'U') IS NULL
BEGIN
    RAISERROR(N'Таблица dbo.TradeInFunnel не найдена. Сначала выполните scripts/mssql_create_tradeinfunnel.sql', 16, 1);
    RETURN;
END
GO

-- Номер РЛ ОП (источник / footing)
IF COL_LENGTH(N'dbo.TradeInFunnel', N'SourceOpRlkNumber') IS NULL
BEGIN
    ALTER TABLE dbo.TradeInFunnel
        ADD SourceOpRlkNumber NVARCHAR(255) NULL;
    PRINT N'Добавлен столбец SourceOpRlkNumber';
END
ELSE
    PRINT N'Столбец SourceOpRlkNumber уже есть';
GO

-- Дата РЛ ОП (источник / footing)
IF COL_LENGTH(N'dbo.TradeInFunnel', N'SourceOpRlkDate') IS NULL
BEGIN
    ALTER TABLE dbo.TradeInFunnel
        ADD SourceOpRlkDate DATETIME2(0) NULL;
    PRINT N'Добавлен столбец SourceOpRlkDate';
END
ELSE
    PRINT N'Столбец SourceOpRlkDate уже есть';
GO

PRINT N'Готово: dbo.TradeInFunnel готов к выгрузке SourceOpRlkNumber / SourceOpRlkDate.';
GO
