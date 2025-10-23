using Microsoft.AspNetCore.Mvc;
using backend.Services;
using backend.Models;
using Microsoft.Extensions.Logging; // Import for logging

namespace backend.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class PhoneSwapRequestController : ControllerBase
    {
        private readonly IPhoneSwapRequestService _swapRequestService;
        private readonly ILogger<PhoneSwapRequestController> _logger; // Logger

        public PhoneSwapRequestController(IPhoneSwapRequestService swapRequestService, ILogger<PhoneSwapRequestController> logger)
        {
            _swapRequestService = swapRequestService;
            _logger = logger; // Initialize logger
        }

        [HttpPost("request")]
        public async Task<IActionResult> CreateRequest([FromBody] PhoneSwapRequestDto request)
        {
            if (request == null)
            {
                _logger.LogError("Invalid phone swap request received (null request body)."); // Log error
                return BadRequest("Invalid request data.");
            }

            try
            {
                await _swapRequestService.CreateSwapRequestAsync(request);
                _logger.LogInformation($"Phone swap request created successfully for email: {request.ContactEmail}."); // Log success
                return Ok("Phone swap request submitted successfully!");
            }
            catch (Exception ex)
            {
                _logger.LogError($"Error creating phone swap request for email: {request.ContactEmail}. Error: {ex.Message}"); // Log error
                return StatusCode(500, "An error occurred while processing your request. Please try again later.");
            }
        }
    }
}