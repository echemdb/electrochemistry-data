**Added:**

* Added the working electrode area reported in the publication to ``atkin_2011_situ_6849``, ``atkin_2014_structure_44``, ``borisenko_2006_situ_6250``, ``borisenko_2012_situ_1736``, ``gasparotto_2009_situ_11140`` (``0.3 cm2``) and ``jovic_1999_cyclic_247`` (``0.316 cm2``). Areas defined by an O-ring are marked with ``effectiveElectrodeSurfaceArea`` in the quantity comment.
* Added the working electrode area of ``alves_2011_electrochemistry_6010`` (``0.283 cm2``), calculated from the 6 mm O-ring of the flow cell.
* Added electrode diameters reported in the publications to ``abe_2019_electro-oxidation_315``, ``abou_2003_electrosorption_211``, ``clavilier_1980_preparation_205``, ``ganassin_2015_non-covalent_8349``, ``meng_2012_hydrogen_5222``, ``wandlowski_1996_structural_10277`` and ``wang_1996_ordered_6672``.
* Added comments on the origin of the electrode area or diameter to ``friedl_2017_interface_216``, ``hermann_2021_effect_138279``, ``schonig_2023_entropic_5948`` and ``tiwari_2020_fingerprint_1450``.

**Fixed:**

* Fixed invalid ``geometricElectrolyteContactArea`` of the working electrode in 43 entries (#181). The key is removed where the publication does not report an area; the electrode diameter from the publication is recorded in ``shape.diameter`` instead (``briega-martos_2020_hydrogen_135452``, ``briega-martos_2021_cation_48``, ``chen_2024_deconvolution_4958``, ``cuesta_2000_adsorption_5684``, ``engstfeld_2018_polycrystalline_17743``, ``sato_2006_effect_725``).
* Fixed the working electrode area of ``jerkiewicz_2009_effect_12309`` (``0.0431 cm2`` instead of ``4.31 1 / mm2``) and the electrode diameter, using the values and uncertainties reported in the publication.
* Fixed the electrode diameter of ``engstfeld_2018_polycrystalline_17743`` (6 mm sample in the hanging meniscus cell, 8 mm sample in the flow cell) and described how the electrolyte contact area is defined in each cell.
* Fixed ``durand_1992_situ_1977``: added the working electrode area (``1.12 cm2``) and dimensions, corrected the crystallographic orientation (``100`` instead of ``110``), the reference electrode (SCE instead of RHE), and the swapped value and unit of the Ar pressure.
* Fixed empty ``shape.height`` entries without a value in ``briega-martos_2020_hydrogen_135452``, ``briega-martos_2021_cation_48`` and ``chen_2024_deconvolution_4958``.
* Fixed the working electrode of ``howlett_2006_electrochemistry_1483``: removed the area of ``1 cm2``, which the publication does not report.
* Fixed the working electrode type of the Au(111) films on mica (``atkin_2009_afm_13266``, ``atkin_2011_situ_6849``, ``atkin_2014_structure_44``, ``borisenko_2006_situ_6250``, ``borisenko_2012_situ_1736``, ``endres_2006_probing_1377``, ``gasparotto_2009_situ_11140``) from ``single crystal`` to ``highly oriented thin film``.
* Fixed ``blizanac_2004_anion_625`` by removing the electrode diameter, which was derived from the area and not reported in the publication.
