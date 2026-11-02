using Serilog.Core;
using Serilog.Events;

internal sealed class ExportDiagnostics : ILogEventSink
{
    private static int _errors;
    public static int Errors => Volatile.Read(ref _errors);

    public void Emit(LogEvent logEvent)
    {
        if (logEvent.Level >= LogEventLevel.Error)
            Interlocked.Increment(ref _errors);
    }
}
