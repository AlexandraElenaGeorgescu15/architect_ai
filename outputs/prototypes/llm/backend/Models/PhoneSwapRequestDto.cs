namespace backend.Models
{
    public class PhoneSwapRequestDto
    {
        public string CurrentPhone { get; set; } = string.Empty;
        public string DesiredPhone { get; set; } = string.Empty;
        public string Reason { get; set; } = string.Empty;
        public string ContactEmail { get; set; } = string.Empty;
        public string ContactPhone { get; set; } = string.Empty;
    }
}