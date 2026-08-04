import gov.usgs.earthquake.nshmp.fault.surface.RuptureSurface;
import gov.usgs.earthquake.nshmp.geo.Location;
import gov.usgs.earthquake.nshmp.model.Distance;
import gov.usgs.earthquake.nshmp.model.HazardModel;
import gov.usgs.earthquake.nshmp.model.Rupture;
import gov.usgs.earthquake.nshmp.model.RuptureSet;
import gov.usgs.earthquake.nshmp.model.Source;
import gov.usgs.earthquake.nshmp.model.SourceTree;
import gov.usgs.earthquake.nshmp.tree.Branch;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.io.OutputStream;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.zip.GZIPOutputStream;

public final class AuthoritativeRuptureSiteDistances {

  private AuthoritativeRuptureSiteDistances() {}

  public static void main(String[] args) throws Exception {

    if (args.length != 5) {
      throw new IllegalArgumentException(
          "Expected model root, rupture TSV, site TSV, distance CSV.gz, "
          + "and rupture-audit CSV.gz.");
    }

    Path modelRoot = Path.of(args[0]).toAbsolutePath().normalize();
    Path ruptureInput = Path.of(args[1]).toAbsolutePath().normalize();
    Path siteInput = Path.of(args[2]).toAbsolutePath().normalize();
    Path distanceOutput = Path.of(args[3]).toAbsolutePath().normalize();
    Path auditOutput = Path.of(args[4]).toAbsolutePath().normalize();

    HazardModel model = HazardModel.load(modelRoot);
    List<SiteRecord> sites = readSites(siteInput);

    int ruptureCount = 0;
    long distanceCount = 0L;
    String observedChunkId = "";

    try (
        BufferedReader reader = Files.newBufferedReader(
            ruptureInput, StandardCharsets.UTF_8);
        PrintWriter distanceWriter = openWriter(distanceOutput);
        PrintWriter auditWriter = openWriter(auditOutput)
    ) {

      String headerLine = reader.readLine();
      if (headerLine == null) {
        throw new IllegalArgumentException("Rupture TSV is empty.");
      }
      Map<String, Integer> columns = headerMap(headerLine);

      distanceWriter.println(String.join(",",
          "chunk_id", "rupture_ordinal", "site_ordinal", "rupture_id",
          "site_id", "r_jb_km", "r_rup_km", "r_x_km", "retrieval_error"));

      auditWriter.println(String.join(",",
          "chunk_id", "rupture_ordinal", "event_id", "rupture_id",
          "expected_tree_id", "retrieved_tree_id",
          "expected_branch_index", "retrieved_branch_index",
          "retrieved_branch_id", "retrieved_branch_weight",
          "expected_rupture_set_id", "retrieved_rupture_set_id",
          "expected_source_index", "expected_source_id", "retrieved_source_id",
          "expected_source_name", "retrieved_source_name",
          "expected_source_type", "retrieved_source_type",
          "expected_rupture_index", "expected_magnitude", "retrieved_magnitude",
          "expected_raw_rate", "retrieved_raw_rate", "retrieved_rake_deg",
          "expected_top_depth_km", "surface_depth_km",
          "expected_width_km", "surface_width_km",
          "surface_dip_deg", "surface_strike_deg",
          "expected_centroid_longitude", "surface_centroid_longitude",
          "expected_centroid_latitude", "surface_centroid_latitude",
          "expected_centroid_depth_km", "surface_centroid_depth_km",
          "surface_class", "retrieval_error"));

      String line;
      while ((line = reader.readLine()) != null) {
        if (line.isBlank()) continue;
        String[] values = line.split("\\t", -1);

        String chunkId = get(values, columns, "chunk_id");
        observedChunkId = chunkId;
        int ruptureOrdinal = parseInt(get(values, columns, "rupture_ordinal"));
        String eventId = get(values, columns, "event_id");
        String ruptureId = get(values, columns, "rupture_id");
        int treeId = parseInt(get(values, columns, "tree_id"));
        int branchIndex = parseInt(get(values, columns, "branch_index"));
        int ruptureSetId = parseInt(get(values, columns, "rupture_set_id"));
        int sourceIndex = parseInt(get(values, columns, "source_index"));
        int sourceId = parseInt(get(values, columns, "source_id"));
        String sourceName = get(values, columns, "source_name");
        String sourceType = get(values, columns, "source_type");
        int ruptureIndex = parseInt(get(values, columns, "rupture_index"));
        double magnitude = parseDouble(get(values, columns, "magnitude"));
        double rawRate = parseDouble(get(values, columns, "raw_annual_rate"));
        double topDepth = parseDouble(get(values, columns, "top_depth_km"));
        double width = parseDouble(get(values, columns, "width_km"));
        double centroidLon = parseDoubleOrNaN(
            get(values, columns, "centroid_longitude"));
        double centroidLat = parseDoubleOrNaN(
            get(values, columns, "centroid_latitude"));
        double centroidDepth = parseDoubleOrNaN(
            get(values, columns, "centroid_depth_km"));

        int retrievedTreeId = -1;
        int retrievedBranchIndex = -1;
        String retrievedBranchId = "";
        double retrievedBranchWeight = Double.NaN;
        int retrievedRuptureSetId = -1;
        int retrievedSourceId = -1;
        String retrievedSourceName = "";
        String retrievedSourceType = "";
        double retrievedMagnitude = Double.NaN;
        double retrievedRate = Double.NaN;
        double retrievedRake = Double.NaN;
        double surfaceDepth = Double.NaN;
        double surfaceWidth = Double.NaN;
        double surfaceDip = Double.NaN;
        double surfaceStrike = Double.NaN;
        double surfaceCentroidLon = Double.NaN;
        double surfaceCentroidLat = Double.NaN;
        double surfaceCentroidDepth = Double.NaN;
        String surfaceClass = "";
        String retrievalError = "";
        RuptureSurface surface = null;

        try {
          Optional<SourceTree> treeOptional = model.tree(treeId);
          if (treeOptional.isEmpty()) {
            throw new IllegalArgumentException("Tree not found: " + treeId);
          }
          SourceTree tree = treeOptional.get();
          retrievedTreeId = tree.id();

          BranchMatch match = resolveBranch(
              tree, branchIndex, ruptureSetId, sourceIndex, sourceId,
              sourceName, sourceType, ruptureIndex, magnitude, rawRate);

          retrievedBranchIndex = match.index;
          Branch<RuptureSet<? extends Source>> branch = match.branch;
          retrievedBranchId = branch.id();
          retrievedBranchWeight = branch.weight();

          RuptureSet<? extends Source> ruptureSet = branch.value();
          retrievedRuptureSetId = ruptureSet.id();
          Source source = ruptureSet.get(sourceIndex);
          retrievedSourceId = source.id();
          retrievedSourceName = source.name();
          retrievedSourceType = source.type().name();
          Rupture rupture = source.get(ruptureIndex);
          retrievedMagnitude = rupture.mag();
          retrievedRate = rupture.rate();
          retrievedRake = rupture.rake();
          surface = rupture.surface();
          surfaceClass = surface.getClass().getName();

          final RuptureSurface resolvedSurface = surface;
          surfaceDepth = safe(() -> resolvedSurface.depth());
          surfaceWidth = safe(() -> resolvedSurface.width());
          surfaceDip = safe(() -> resolvedSurface.dip());
          surfaceStrike = safe(() -> resolvedSurface.strike());

          try {
            Location centroid = surface.centroid();
            if (centroid != null) {
              surfaceCentroidLon = centroid.longitude;
              surfaceCentroidLat = centroid.latitude;
              surfaceCentroidDepth = centroid.depth;
            }
          } catch (RuntimeException exception) {
            surfaceCentroidLon = Double.NaN;
            surfaceCentroidLat = Double.NaN;
            surfaceCentroidDepth = Double.NaN;
          }

        } catch (Exception exception) {
          retrievalError = errorText(exception);
        }

        auditWriter.println(String.join(",",
            csv(chunkId), integer(ruptureOrdinal), csv(eventId), csv(ruptureId),
            integer(treeId), integer(retrievedTreeId),
            integer(branchIndex), integer(retrievedBranchIndex),
            csv(retrievedBranchId), number(retrievedBranchWeight),
            integer(ruptureSetId), integer(retrievedRuptureSetId),
            integer(sourceIndex), integer(sourceId), integer(retrievedSourceId),
            csv(sourceName), csv(retrievedSourceName),
            csv(sourceType), csv(retrievedSourceType),
            integer(ruptureIndex), number(magnitude), number(retrievedMagnitude),
            number(rawRate), number(retrievedRate), number(retrievedRake),
            number(topDepth), number(surfaceDepth), number(width),
            number(surfaceWidth), number(surfaceDip), number(surfaceStrike),
            number(centroidLon), number(surfaceCentroidLon),
            number(centroidLat), number(surfaceCentroidLat),
            number(centroidDepth), number(surfaceCentroidDepth),
            csv(surfaceClass), csv(retrievalError)));

        for (SiteRecord site : sites) {
          double rJB = Double.NaN;
          double rRup = Double.NaN;
          double rX = Double.NaN;
          String distanceError = retrievalError;

          if (distanceError.isEmpty() && surface != null) {
            try {
              Distance distance = surface.distanceTo(site.location);
              rJB = distance.rJB;
              rRup = distance.rRup;
              rX = distance.rX;
            } catch (Exception exception) {
              distanceError = errorText(exception);
            }
          }

          distanceWriter.println(String.join(",",
              csv(chunkId), integer(ruptureOrdinal), integer(site.siteOrdinal),
              csv(ruptureId), csv(site.siteId), number(rJB), number(rRup),
              number(rX), csv(distanceError)));
          distanceCount++;
        }
        ruptureCount++;
      }

      if (distanceWriter.checkError()) {
        throw new IOException("Error writing distance output.");
      }
      if (auditWriter.checkError()) {
        throw new IOException("Error writing rupture-audit output.");
      }
    }

    System.out.println("AUTHORITATIVE_DISTANCE_CHUNK_COMPLETE");
    System.out.println("chunk_id=" + observedChunkId);
    System.out.println("ruptures=" + ruptureCount);
    System.out.println("sites=" + sites.size());
    System.out.println("distance_rows=" + distanceCount);
  }

  private static BranchMatch resolveBranch(
      SourceTree tree,
      int expectedBranchIndex,
      int ruptureSetId,
      int sourceIndex,
      int sourceId,
      String sourceName,
      String sourceType,
      int ruptureIndex,
      double magnitude,
      double rawRate
  ) {

    if (expectedBranchIndex >= 0 && expectedBranchIndex < tree.size()) {
      Branch<RuptureSet<? extends Source>> candidate =
          tree.get(expectedBranchIndex);
      if (compatible(candidate, ruptureSetId, sourceIndex, sourceId,
          sourceName, sourceType, ruptureIndex, magnitude, rawRate)) {
        return new BranchMatch(expectedBranchIndex, candidate);
      }
    }

    int ruptureSetMatches = 0;
    int compatibleMatches = 0;
    BranchMatch first = null;

    for (int index = 0; index < tree.size(); index++) {
      Branch<RuptureSet<? extends Source>> candidate = tree.get(index);
      if (candidate.value().id() == ruptureSetId) ruptureSetMatches++;
      if (!compatible(candidate, ruptureSetId, sourceIndex, sourceId,
          sourceName, sourceType, ruptureIndex, magnitude, rawRate)) {
        continue;
      }
      compatibleMatches++;
      if (first == null) first = new BranchMatch(index, candidate);
    }

    if (first == null) {
      throw new IllegalArgumentException(
          "No compatible branch for rupture-set " + ruptureSetId
          + " in tree " + tree.id()
          + "; expected branch index=" + expectedBranchIndex
          + "; rupture-set matches=" + ruptureSetMatches
          + "; compatible matches=" + compatibleMatches);
    }
    return first;
  }

  private static boolean compatible(
      Branch<RuptureSet<? extends Source>> candidate,
      int ruptureSetId,
      int sourceIndex,
      int sourceId,
      String sourceName,
      String sourceType,
      int ruptureIndex,
      double magnitude,
      double rawRate
  ) {
    RuptureSet<? extends Source> ruptureSet = candidate.value();
    if (ruptureSet.id() != ruptureSetId) return false;
    if (sourceIndex < 0 || sourceIndex >= ruptureSet.size()) return false;
    Source source = ruptureSet.get(sourceIndex);
    if (source.id() != sourceId) return false;
    if (!source.name().equals(sourceName)) return false;
    if (!source.type().name().equals(sourceType)) return false;
    if (ruptureIndex < 0 || ruptureIndex >= source.size()) return false;
    Rupture rupture = source.get(ruptureIndex);
    if (Math.abs(rupture.mag() - magnitude) > 1.0e-10) return false;
    double scale = Math.max(Math.abs(rupture.rate()), Math.abs(rawRate));
    double tolerance = Math.max(1.0e-18, 1.0e-12 * scale);
    return Math.abs(rupture.rate() - rawRate) <= tolerance;
  }

  private static List<SiteRecord> readSites(Path path) throws IOException {
    List<SiteRecord> sites = new ArrayList<>();
    try (BufferedReader reader = Files.newBufferedReader(
        path, StandardCharsets.UTF_8)) {
      String headerLine = reader.readLine();
      if (headerLine == null) throw new IllegalArgumentException("Empty site TSV.");
      Map<String, Integer> columns = headerMap(headerLine);
      String line;
      while ((line = reader.readLine()) != null) {
        if (line.isBlank()) continue;
        String[] values = line.split("\\t", -1);
        int ordinal = parseInt(get(values, columns, "site_ordinal"));
        String siteId = get(values, columns, "site_id");
        double longitude = parseDouble(get(values, columns, "longitude"));
        double latitude = parseDouble(get(values, columns, "latitude"));
        sites.add(new SiteRecord(
            ordinal, siteId, Location.create(longitude, latitude)));
      }
    }
    if (sites.isEmpty()) throw new IllegalArgumentException("No sites were read.");
    return sites;
  }

  private static Map<String, Integer> headerMap(String headerLine) {
    String[] header = headerLine.split("\\t", -1);
    Map<String, Integer> columns = new HashMap<>();
    for (int index = 0; index < header.length; index++) {
      columns.put(header[index], index);
    }
    return columns;
  }

  private static PrintWriter openWriter(Path path) throws IOException {
    Files.createDirectories(path.getParent());
    OutputStream output = Files.newOutputStream(path);
    if (path.getFileName().toString().toLowerCase(Locale.ROOT).endsWith(".gz")) {
      output = new GZIPOutputStream(output, 1024 * 1024);
    }
    return new PrintWriter(new BufferedWriter(new OutputStreamWriter(
        output, StandardCharsets.UTF_8), 1024 * 1024));
  }

  private static double safe(java.util.function.DoubleSupplier supplier) {
    try {
      return supplier.getAsDouble();
    } catch (RuntimeException exception) {
      return Double.NaN;
    }
  }

  private static String errorText(Exception exception) {
    String message = String.valueOf(exception.getMessage())
        .replace('\r', ' ').replace('\n', ' ');
    return exception.getClass().getName() + ": " + message;
  }

  private static String get(
      String[] values, Map<String, Integer> columns, String name) {
    Integer index = columns.get(name);
    if (index == null || index < 0 || index >= values.length) {
      throw new IllegalArgumentException("Missing input column: " + name);
    }
    return values[index];
  }

  private static int parseInt(String value) {
    return (int) Math.round(Double.parseDouble(value));
  }

  private static double parseDouble(String value) {
    return Double.parseDouble(value);
  }

  private static double parseDoubleOrNaN(String value) {
    return value == null || value.isBlank()
        ? Double.NaN
        : Double.parseDouble(value);
  }

  private static String integer(int value) {
    return Integer.toString(value);
  }

  private static String number(double value) {
    return String.format(Locale.US, "%.17g", value);
  }

  private static String csv(String value) {
    if (value == null) return "";
    boolean quote = value.contains(",") || value.contains("\"")
        || value.contains("\n") || value.contains("\r");
    if (!quote) return value;
    return "\"" + value.replace("\"", "\"\"") + "\"";
  }

  private static final class SiteRecord {
    final int siteOrdinal;
    final String siteId;
    final Location location;

    SiteRecord(int siteOrdinal, String siteId, Location location) {
      this.siteOrdinal = siteOrdinal;
      this.siteId = siteId;
      this.location = location;
    }
  }

  private static final class BranchMatch {
    final int index;
    final Branch<RuptureSet<? extends Source>> branch;

    BranchMatch(int index, Branch<RuptureSet<? extends Source>> branch) {
      this.index = index;
      this.branch = branch;
    }
  }
}
