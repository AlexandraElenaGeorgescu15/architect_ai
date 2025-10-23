using backend.Models;
using backend.Data;
namespace backend.Services
{
    public interface IPhoneSwapRequestService
    {
        Task CreateSwapRequestAsync(PhoneSwapRequestDto request);
    }

    public class PhoneSwapRequestService : IPhoneSwapRequestService
    {
        private readonly IPhoneSwapRequestRepository _swapRequestRepository;

        public PhoneSwapRequestService(IPhoneSwapRequestRepository swapRequestRepository)
        {
            _swapRequestRepository = swapRequestRepository;
        }

        public async Task CreateSwapRequestAsync(PhoneSwapRequestDto request)
        {
            // Here, you could add validation logic, data transformation, etc.
            // For example, check if the requested phones are valid and available.

            // Persist the request to the database using the repository
            await _swapRequestRepository.AddRequestAsync(request);
        }
    }
}