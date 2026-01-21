// MongoDB Atlas Shell Script for Cleanup
// Run this in MongoDB Atlas Shell or MongoDB Compass

use ids_db;

print("=== Current State ===");
var benignCount = db.training_data.countDocuments({ label: "benign" });
var maliciousCount = db.training_data.countDocuments({ label: { $ne: "benign" } });
var total = benignCount + maliciousCount;

print("Total: " + total);
print("Benign: " + benignCount + " (" + (benignCount/total*100).toFixed(1) + "%)");
print("Malicious: " + maliciousCount + " (" + (maliciousCount/total*100).toFixed(1) + "%)");

print("\n=== Target ===");
var targetBenign = 22651;  // Use all available
var targetMalicious = 15100;  // For 60:40 ratio
var targetTotal = targetBenign + targetMalicious;
print("Target total: " + targetTotal);
print("Target benign: " + targetBenign + " (60.0%)");
print("Target malicious: " + targetMalicious + " (40.0%)");

print("\n=== Cleanup Plan ===");
var deleteMalicious = maliciousCount - targetMalicious;
print("Will delete " + deleteMalicious + " malicious documents");

// Get random sample of malicious IDs to KEEP
print("\nSampling malicious documents to keep...");
var keepMalicious = db.training_data.aggregate([
  { $match: { label: { $ne: "benign" } } },
  { $sample: { size: targetMalicious } },
  { $project: { _id: 1 } }
]).toArray().map(d => d._id);

print("Found " + keepMalicious.length + " malicious documents to keep");

// Delete all malicious EXCEPT the ones to keep
print("\nDeleting excess malicious documents...");
var deleteResult = db.training_data.deleteMany({
  label: { $ne: "benign" },
  _id: { $nin: keepMalicious }
});

print("Deleted: " + deleteResult.deletedCount + " documents");

// Verify
print("\n=== Final State ===");
var finalBenign = db.training_data.countDocuments({ label: "benign" });
var finalMalicious = db.training_data.countDocuments({ label: { $ne: "benign" } });
var finalTotal = finalBenign + finalMalicious;

print("Total: " + finalTotal);
print("Benign: " + finalBenign + " (" + (finalBenign/finalTotal*100).toFixed(1) + "%)");
print("Malicious: " + finalMalicious + " (" + (finalMalicious/finalTotal*100).toFixed(1) + "%)");

print("\n✓ Cleanup complete!");
